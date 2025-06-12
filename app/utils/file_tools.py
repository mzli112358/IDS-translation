import os
import PyPDF2
from io import BytesIO
from flask import current_app

def extract_text_from_pdf(file_path):
    """
    从PDF提取文本
    返回: (success: bool, text: str, error: str)
    """
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = "\n".join([page.extract_text() for page in reader.pages])
            return True, text, None
            
    except Exception as e:
        current_app.logger.error(f"PDF提取失败: {str(e)}")
        return False, None, str(e)

def validate_pdf(file_stream):
    """验证PDF文件有效性"""
    try:
        PyPDF2.PdfReader(BytesIO(file_stream.read()))
        file_stream.seek(0)
        return True
    except:
        file_stream.seek(0)
        return False