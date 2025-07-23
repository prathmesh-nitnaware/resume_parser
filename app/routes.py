from flask import Blueprint, render_template, request, redirect, flash, current_app, send_file, url_for, send_from_directory
import os
import csv
from io import StringIO
from werkzeug.utils import secure_filename
from .parser import parse_pdf_resume, parse_docx_resume
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
            flash('⚠️ No file part in request.')
            return redirect(request.url)

        files = request.files.getlist('resumes')

        success_count = 0
        for file in files:
            if file.filename == '':
                continue

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                parsed_data = {}
                if filename.endswith('.pdf'):
                    parsed_data = parse_pdf_resume(filepath)
                elif filename.endswith('.docx'):
                    parsed_data = parse_docx_resume(filepath)

                resume_entry = Resume(
                    filename=filename,
                    name=parsed_data.get('name'),
                    email=parsed_data.get('email'),
                    phone=parsed_data.get('phone'),
                    skills=", ".join(parsed_data.get('skills', []))
                )
                db.session.add(resume_entry)
                success_count += 1

        db.session.commit()
        flash(f"✅ Successfully parsed and stored {success_count} resume(s).")
        return redirect(request.url)

    return render_template('index.html')

@main.route('/dashboard', methods=['GET'])
def dashboard():
    query = request.args.get('q', '').lower()
    if query:
        resumes = Resume.query.filter(
            (Resume.name.ilike(f"%{query}%")) |
            (Resume.skills.ilike(f"%{query}%"))
        ).all()
    else:
        resumes = Resume.query.all()
    return render_template('dashboard.html', resumes=resumes, query=query)

@main.route('/export', methods=['GET'])
def export_csv():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Filename', 'Name', 'Email', 'Phone', 'Skills'])

    resumes = Resume.query.all()
    for r in resumes:
        writer.writerow([r.id, r.filename, r.name, r.email, r.phone, r.skills])

    output.seek(0)
    return send_file(
        output,
        mimetype='text/csv',
        download_name='resumes.csv',
        as_attachment=True
    )

@main.route('/delete/<int:id>', methods=['POST'])
def delete_resume(id):
    resume = Resume.query.get_or_404(id)

    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], resume.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(resume)
    db.session.commit()
    flash(f"🗑️ Resume '{resume.filename}' deleted successfully.")
    return redirect(url_for('main.dashboard'))

@main.route('/download/<filename>', methods=['GET'])
def download_resume(filename):
    uploads_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(uploads_folder, filename, as_attachment=True)
