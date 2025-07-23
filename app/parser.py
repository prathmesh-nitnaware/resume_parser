import pdfplumber
import docx
import re
import spacy
import os

nlp = spacy.load("en_core_web_sm")

def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+', text)
    return match.group(0) if match else None

def extract_phone(text):
    match = re.search(r'(\+91[\s\-]?)?[0]?[789]\d{9}', text)
    return match.group(0) if match else None

def extract_name(text):
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text
    return None

def extract_skills(text):
    skill_keywords = [
        'python', 'java', 'c++', 'sql', 'html', 'css', 'javascript',
        'django', 'flask', 'react', 'node', 'excel', 'communication',
        'leadership', 'machine learning', 'deep learning'
    ]
    text_lower = text.lower()
    return [skill for skill in skill_keywords if skill in text_lower]

def parse_pdf_resume(file_path):
    text = extract_text_from_pdf(file_path)
    return {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": extract_skills(text)
    }

def parse_docx_resume(file_path):
    text = extract_text_from_docx(file_path)
    return {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": extract_skills(text)
    }

# Optional: Common wrapper if needed in future
def parse_resume(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        return parse_pdf_resume(file_path)
    elif ext == '.docx':
        return parse_docx_resume(file_path)
    else:
        return {}
