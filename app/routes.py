import os
import csv
from io import StringIO
from collections import Counter
from flask import (
    Blueprint, render_template, request, redirect, flash, 
    current_app, url_for, Response, send_from_directory
)
from werkzeug.utils import secure_filename
from docx2pdf import convert
from sqlalchemy import or_, and_
from .parser import parse_pdf_resume, parse_docx_resume, score_resumes
from .models import Resume
from . import db

main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'resumes' not in request.files:
            flash('No file part in the request.', 'error')
            return redirect(request.url)

        files = request.files.getlist('resumes')
        success_count = 0
        error_files = []

        if not files or files[0].filename == '':
            flash('No files selected for uploading.', 'error')
            return redirect(request.url)

        for file in files:
            if file and allowed_file(file.filename):
                try:
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)

                    if filename.endswith('.pdf'):
                        parsed_data = parse_pdf_resume(filepath)
                    elif filename.endswith('.docx'):
                        parsed_data = parse_docx_resume(filepath)
                    
                    existing_resume = Resume.query.filter_by(filename=filename).first()
                    if existing_resume:
                        db.session.delete(existing_resume)
                        db.session.commit()

                    resume_entry = Resume(
                        filename=filename,
                        name=parsed_data.get('name', 'N/A'),
                        email=parsed_data.get('email', 'N/A'),
                        phone=parsed_data.get('phone', 'N/A'),
                        skills=", ".join(parsed_data.get('skills', []))
                    )
                    db.session.add(resume_entry)
                    success_count += 1
                except Exception as e:
                    current_app.logger.error(f"Error processing {file.filename}: {e}")
                    error_files.append(file.filename)
            elif file.filename != '':
                error_files.append(file.filename)
        
        db.session.commit()

        if success_count > 0:
            flash(f"✅ Successfully parsed {success_count} resume(s).", 'success')
        if error_files:
            flash(f"⚠️ Failed to process {len(error_files)} file(s): {', '.join(error_files)}.", 'error')

        return redirect(url_for('main.index'))
    
    return render_template('index.html')

@main.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    job_description = request.form.get('job_description', '').strip()
    query = request.args.get('q', '').strip()

    base_query = Resume.query
    if query:
        search_terms = [term.strip().lower() for term in query.split(',')]
        name_query = Resume.name.ilike(f"%{search_terms[0]}%")
        skill_queries = [Resume.skills.ilike(f"%{term}%") for term in search_terms]
        base_query = base_query.filter(or_(name_query, and_(*skill_queries)))
    
    resumes = base_query.all()
    
    if request.method == 'POST' and job_description:
        resumes = score_resumes(job_description, resumes)
    else:
        for resume in resumes:
            resume.score = 0

    average_score = 0
    top_5_skills = []
    if resumes:
        total_scores = [r.score for r in resumes if hasattr(r, 'score')]
        average_score = sum(total_scores) / len(total_scores) if total_scores else 0
        
        all_skills = []
        for r in resumes:
            all_skills.extend([skill.strip().lower() for skill in r.skills.split(',') if skill.strip()])
        
        skill_counts = Counter(all_skills)
        top_5_skills = skill_counts.most_common(5)

    recent_resumes = Resume.query.order_by(Resume.date_uploaded.desc()).limit(3).all()

    return render_template(
        'dashboard.html',
        resumes=resumes,
        query=query,
        job_description=job_description,
        average_score=int(average_score),
        top_skills=top_5_skills,
        recent_resumes=recent_resumes
    )

@main.route('/preview/<path:filename>')
def preview_resume(filename):
    uploads_folder = current_app.config['UPLOAD_FOLDER']
    source_path = os.path.join(uploads_folder, filename)

    if not os.path.exists(source_path):
        flash("File not found for preview.", "error")
        return redirect(url_for('main.dashboard'))

    if filename.lower().endswith('.docx'):
        pdf_filename = f"{os.path.splitext(filename)[0]}.pdf"
        pdf_path = os.path.join(uploads_folder, pdf_filename)
        
        if not os.path.exists(pdf_path):
             try:
                convert(source_path, pdf_path)
             except Exception as e:
                current_app.logger.error(f"Could not convert {filename} to PDF: {e}")
                flash(f"Could not generate a preview for {filename}.", "error")
                return redirect(url_for('main.dashboard'))
        
        return send_from_directory(uploads_folder, pdf_filename)
    
    elif filename.lower().endswith('.pdf'):
        return send_from_directory(uploads_folder, filename)
    
    else:
        flash("Preview is only available for PDF and DOCX files.", "error")
        return redirect(url_for('main.dashboard'))

@main.route('/export', methods=['GET'])
def export_csv():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Filename', 'Name', 'Email', 'Phone', 'Skills', 'Date Uploaded'])
    
    resumes = Resume.query.all()
    for resume in resumes:
        writer.writerow([resume.id, resume.filename, resume.name, resume.email, resume.phone, resume.skills, resume.date_uploaded.strftime('%Y-%m-%d %H:%M:%S')])
    
    output.seek(0)
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=resumes.csv"}
    )

@main.route('/download/<path:filename>', methods=['GET'])
def download_resume(filename):
    uploads_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(uploads_folder, filename, as_attachment=True)

@main.route('/delete/<int:id>', methods=['POST'])
def delete_resume(id):
    resume = db.session.get(Resume, id)
    if not resume:
        flash('Resume not found.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], resume.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        
        pdf_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{os.path.splitext(resume.filename)[0]}.pdf")
        if os.path.exists(pdf_filepath):
            os.remove(pdf_filepath)

    except Exception as e:
        current_app.logger.error(f"Error deleting file {resume.filename}: {e}")

    db.session.delete(resume)
    db.session.commit()
    
    flash(f"🗑️ Resume '{resume.filename}' has been deleted.", 'success')
    return redirect(url_for('main.dashboard'))