import os
from flask import current_app
from werkzeug.utils import secure_filename
from app.utils.validators import validate_file_extension, validate_file_size

def process_uploaded_file(file_stream, patent_number=None):
    """
    处理上传的专利文件
    返回: (success: bool, file_path: str, error: str)
    """
    try:
        # 验证文件
        if not validate_file_extension(file_stream.filename):
            return False, None, "不支持的文件类型"
        
        if not validate_file_size(file_stream):
            max_mb = current_app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)
            return False, None, f"文件超过{max_mb}MB限制"

        # 保存文件
        filename = f"{patent_number or 'temp'}_{secure_filename(file_stream.filename)}"
        save_path = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            filename
        )
        
        file_stream.save(save_path)
        return True, save_path, None

    except Exception as e:
        current_app.logger.error(f"文件处理失败: {str(e)}")
        return False, None, "服务器处理文件时出错"