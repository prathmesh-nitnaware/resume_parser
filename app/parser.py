from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import PyPDF2
from docx import Document
import re

def extract_text_from_pdf(filepath):
    text = ""
    with open(filepath, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def extract_text_from_docx(filepath):
    document = Document(filepath)
    return "\n".join([para.text for para in document.paragraphs])

def extract_contact_info(text):
    email = re.search(r'[\w\.-]+@[\w\.-]+', text)
    phone = re.search(r'(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{10})', text)
    return {
        "email": email.group(0) if email else "N/A",
        "phone": phone.group(0) if phone else "N/A"
    }

def extract_skills(text):
    SKILLS_DB = [
        'python', 'java', 'c++', 'javascript', 'sql', 'html', 'css', 'react', 'node', 'angular',
        'flask', 'django', 'api', 'rest', 'git', 'docker', 'kubernetes', 'aws', 'azure', 'gcp',
        'machine learning', 'deep learning', 'data analysis', 'tensorflow', 'pytorch', 'scikit-learn',
        'mysql', 'postgresql', 'mongodb', 'agile', 'scrum', 'project management'
    ]
    found_skills = set()
    for skill in SKILLS_DB:
        if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
            found_skills.add(skill.capitalize())
    return list(found_skills)

def parse_resume_content(text):
    contact_info = extract_contact_info(text)
    skills = extract_skills(text)
    name = text.split('\n')[0].strip()
    
    return {
        'name': name if len(name) < 40 else "N/A",
        'email': contact_info['email'],
        'phone': contact_info['phone'],
        'skills': skills
    }

def parse_pdf_resume(filepath):
    text = extract_text_from_pdf(filepath)
    return parse_resume_content(text)

def parse_docx_resume(filepath):
    text = extract_text_from_docx(filepath)
    return parse_resume_content(text)

def score_resumes(job_description, resumes):
    if not job_description.strip() or not resumes:
        for resume in resumes:
            resume.score = 0
        return resumes

    resume_skills_list = [resume.skills for resume in resumes]
    documents = [job_description] + resume_skills_list

    try:
        tfidf_vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = tfidf_vectorizer.fit_transform(documents)
        
        cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])

        for i, resume in enumerate(resumes):
            resume.score = int(cosine_similarities[0, i] * 100)
    except ValueError:
        for resume in resumes:
            resume.score = 0
    
    resumes.sort(key=lambda r: r.score, reverse=True)
    return resumes