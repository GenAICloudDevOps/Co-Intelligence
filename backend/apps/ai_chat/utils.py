import PyPDF2
import docx
import boto3
import json
from io import BytesIO
from tavily import TavilyClient
from config import settings

s3_client = boto3.client('s3', region_name=settings.AWS_REGION)
tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY) if settings.TAVILY_API_KEY else None

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file"""
    pdf_file = BytesIO(file_content)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX file"""
    docx_file = BytesIO(file_content)
    doc = docx.Document(docx_file)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def extract_text_from_file(filename: str, file_content: bytes) -> str:
    """Extract text based on file extension"""
    if filename.endswith('.pdf'):
        return extract_text_from_pdf(file_content)
    elif filename.endswith('.docx'):
        return extract_text_from_docx(file_content)
    elif filename.endswith('.txt') or filename.endswith('.md'):
        return file_content.decode('utf-8')
    else:
        raise ValueError(f"Unsupported file type: {filename}")

def upload_to_s3(file_content: bytes, filename: str, session_id: int) -> str:
    """Upload file to S3 and return URL"""
    if not settings.S3_BUCKET_NAME:
        return ""
    
    key = f"chat-documents/{session_id}/{filename}"
    s3_client.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=file_content
    )
    return f"s3://{settings.S3_BUCKET_NAME}/{key}"

def search_web(query: str, max_results: int = 3) -> dict:
    """Search web using Tavily API"""
    if not tavily_client:
        return {"results": [], "error": "Tavily API key not configured"}
    
    try:
        response = tavily_client.search(query, max_results=max_results)
        return {
            "results": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")
                }
                for r in response.get("results", [])
            ],
            "query": query
        }
    except Exception as e:
        return {"results": [], "error": str(e)}

def execute_code(code: str, timeout: int = 30) -> dict:
    """Execute Python code using Lambda and return results"""
    lambda_client = boto3.client('lambda', region_name=settings.AWS_REGION)
    
    try:
        response = lambda_client.invoke(
            FunctionName='co-intelligence-code-executor',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'code': code,
                'timeout': timeout
            })
        )
        
        result = json.loads(response['Payload'].read())
        body = json.loads(result.get('body', '{}'))
        
        return {
            'success': body.get('success', False),
            'output': body.get('output', ''),
            'errors': body.get('errors'),
        }
    except Exception as e:
        return {
            'success': False,
            'output': '',
            'errors': f"Lambda execution failed: {str(e)}"
        }
