import re
from flask import current_app
from werkzeug.utils import secure_filename
from wtforms.validators import ValidationError

import re
from wtforms.validators import ValidationError

def validate_password_strength(password):
    """
    密码强度验证（需满足以下所有条件）：
    1. 长度8-64字符
    2. 包含大小写字母
    3. 包含数字
    4. 可选的特殊字符
    """
    if len(password) < 8:
        raise ValidationError('密码长度至少8个字符')
    if not re.search(r'[A-Z]', password):
        raise ValidationError('密码必须包含大写字母')
    if not re.search(r'[a-z]', password):
        raise ValidationError('密码必须包含小写字母')
    if not re.search(r'\d', password):
        raise ValidationError('密码必须包含数字')
    # 可选：如需特殊字符要求可取消注释
    # if not re.search(r'[^A-Za-z0-9]', password):
    #     raise ValidationError('密码必须包含特殊字符')

# WTForms专用验证器
def validate_password(form, field):
    """用于表单字段的密码验证"""
    validate_password_strength(field.data)
    
class PatentValidator:
    """专利相关验证方法"""
    
    @staticmethod
    def validate_number(patent_number):
        """
        验证并标准化专利号
        返回: (is_valid: bool, normalized: str)
        """
        if not patent_number:
            return False, None

        # 标准化处理
        clean_num = re.sub(r'[\s\-\.]', '', patent_number.upper())
        
        # 中国专利（CN+8-12位数字+可选字母）
        if re.fullmatch(r'^(CN)?\d{8,12}[A-Z]?\d?$', clean_num):
            return True, f"CN{clean_num[2:] if clean_num.startswith('CN') else clean_num}"
            
        # 国际专利（WO+4位年+2字母+5-7数字）
        if re.fullmatch(r'^(WO)?\d{4}[A-Z]{2}\d{5,7}$', clean_num):
            return True, f"WO{clean_num[2:] if clean_num.startswith('WO') else clean_num}"
            
        return False, None

    @staticmethod
    def validate_title(title):
        """验证专利标题（防XSS）"""
        return bool(title) and len(title) <= 500 and re.match(r'^[\w\s\-\.,\u4e00-\u9fa5]+$', title)

class FileValidator:
    """文件验证方法集"""
    
    @staticmethod
    def validate_extension(filename):
        """验证文件扩展名"""
        if not filename:
            return False
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else None
        return ext in current_app.config.get('ALLOWED_EXTENSIONS', {'pdf', 'doc', 'docx'})

    @staticmethod
    def validate_size(file_stream):
        """验证文件大小"""
        file_stream.seek(0, 2)
        size = file_stream.tell()
        file_stream.seek(0)
        return size <= current_app.config.get('MAX_CONTENT_LENGTH', 50 * 1024 * 1024)

    @staticmethod
    def validate_pdf_header(file_stream):
        """验证PDF文件头"""
        header = file_stream.read(4)
        file_stream.seek(0)
        return header == b'%PDF'

# ---------------------------
# WTForms专用验证器（函数式）
# ---------------------------

def validate_patent_number(form, field):
    """WTForms专利号验证"""
    if field.data:
        is_valid, _ = PatentValidator.validate_number(field.data)
        if not is_valid:
            raise ValidationError('专利号格式无效（示例：CN1234567A）')

def validate_file_extension(form, field):
    """WTForms文件扩展名验证"""
    if field.data and not FileValidator.validate_extension(field.data.filename):
        allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'pdf', 'doc', 'docx'})
        raise ValidationError(f"仅支持 {', '.join(allowed)} 格式")

def validate_file_size(form, field):
    """WTForms文件大小验证"""
    if field.data:
        if not FileValidator.validate_size(field.data):
            max_mb = current_app.config.get('MAX_CONTENT_LENGTH', 50 * 1024 * 1024) // (1024 * 1024)
            raise ValidationError(f"文件超过{max_mb}MB限制")
        field.data.seek(0)  # 必须重置指针

def validate_pdf_file(form, field):
    """WTForms PDF文件验证"""
    if field.data:
        validate_file_extension(form, field)
        validate_file_size(form, field)
        if not FileValidator.validate_pdf_header(field.data):
            raise ValidationError("无效的PDF文件")
        field.data.seek(0)