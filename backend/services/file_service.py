"""Centralized file handling service"""
import os
import uuid
from io import BytesIO
import PyPDF2
from docx import Document
import pandas as pd
import aiofiles

TEMP_DIR = "/tmp/co-intelligence"
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {'.csv', '.json', '.xlsx', '.xls', '.pdf', '.docx', '.doc', '.txt'}

os.makedirs(TEMP_DIR, exist_ok=True)

def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF bytes"""
    pdf_file = BytesIO(content)
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX bytes"""
    docx_file = BytesIO(content)
    doc = Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_file(filename: str, content: bytes) -> str:
    """Extract text based on file extension"""
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.pdf':
        return extract_text_from_pdf(content)
    elif ext in ['.docx', '.doc']:
        return extract_text_from_docx(content)
    elif ext in ['.txt', '.md']:
        return content.decode('utf-8')
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def validate_file(filename: str, size: int) -> tuple:
    """Validate file extension and size. Returns (valid, error_message)"""
    ext = os.path.splitext(filename)[1].lower()
    if ext and ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported format: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    if size > MAX_FILE_SIZE:
        return False, f"File too large. Max: {MAX_FILE_SIZE // (1024*1024)}MB"
    return True, None

async def save_temp_file(content: bytes, extension: str) -> str:
    """Save content to temp file and return path"""
    file_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}{extension}")
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)
    return file_path

def cleanup_file(file_path: str):
    """Safely remove a file"""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass

def load_dataframe(file_path: str) -> pd.DataFrame:
    """Load file into pandas DataFrame"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.csv':
        return pd.read_csv(file_path)
    elif ext == '.json':
        return pd.read_json(file_path)
    elif ext in ['.xlsx', '.xls']:
        return pd.read_excel(file_path)
    elif ext == '.pdf':
        text = extract_text_from_pdf(open(file_path, 'rb').read())
        try:
            from io import StringIO
            return pd.read_csv(StringIO(text), sep=None, engine='python')
        except:
            return pd.DataFrame({"raw_text": [text]})
    elif ext in ['.docx', '.doc']:
        text = extract_text_from_docx(open(file_path, 'rb').read())
        try:
            from io import StringIO
            return pd.read_csv(StringIO(text), sep=None, engine='python')
        except:
            return pd.DataFrame({"raw_text": [text]})
    elif ext == '.txt':
        with open(file_path, 'r') as f:
            text = f.read()
        try:
            from io import StringIO
            return pd.read_csv(StringIO(text))
        except:
            return pd.DataFrame({"raw_text": [text]})
    else:
        raise ValueError(f"Unsupported file format: {ext}")
