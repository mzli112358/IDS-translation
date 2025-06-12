import os
import uuid
import json
from datetime import datetime
from flask import (
    Blueprint,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    jsonify,
    render_template
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from typing import Dict, Tuple

from app.models import Submission, File
from app import db
from app.utils.file_parser import PDFParser
from app.utils.validators import validate_patent_number
from app.services.file_processor import process_uploaded_file

upload_bp = Blueprint('upload', __name__, template_folder='templates')

# 配置常量
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB

def allowed_file(filename: str) -> bool:
    """验证文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """文件上传主入口"""
    if request.method == 'POST':
        return _handle_upload_request()
    return render_template('upload/upload.html')

@upload_bp.route('/api/upload', methods=['POST'])
@login_required
def upload_api():
    """
    AJAX文件上传API
    ---
    tags:
      - Upload
    parameters:
      - name: file
        in: formData
        type: file
        required: true
    responses:
      200:
        description: 上传成功
      400:
        description: 无效请求
      413:
        description: 文件过大
      500:
        description: 服务器错误
    """
    # 检查文件大小
    if request.content_length > MAX_CONTENT_LENGTH:
        return jsonify({'error': '文件大小超过50MB限制'}), 413

    if 'file' not in request.files:
        return jsonify({'error': '未选择文件'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': '仅支持PDF/DOC/DOCX格式'}), 400

    try:
        result = _process_upload(file)
        return jsonify({
            'success': True,
            'data': {
                'id': result['submission'].id,
                'patent_number': result['submission'].patent_number,
                'title': result['submission'].title_zh
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"API上传失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

def _handle_upload_request():
    """处理表单上传请求"""
    if 'file' not in request.files:
        flash('未选择文件', 'danger')
        return redirect(request.url)

    file = request.files['file']
    if not file or file.filename == '':
        flash('未选择文件', 'danger')
        return redirect(request.url)

    if not allowed_file(file.filename):
        flash('仅支持PDF/DOC/DOCX格式', 'danger')
        return redirect(request.url)

    try:
        result = _process_upload(file)
        flash('文件上传成功，正在解析...', 'success')
        return redirect(url_for('main.submission_detail', id=result['submission'].id))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"上传处理失败: {str(e)}", exc_info=True)
        flash(f'上传失败: {str(e)}', 'danger')
        return redirect(request.url)

def _process_upload(file) -> Dict:
    """
    处理上传文件核心逻辑
    :param file: 上传的文件对象
    :return: 包含submission和patent_info的字典
    :raises: ValueError 当专利号无效时
    """
    # 生成安全文件名
    file_ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{file_ext}"
    
    # 准备存储路径
    user_upload_dir = os.path.join(
        current_app.config['UPLOAD_FOLDER'], 
        str(current_user.id)
    )
    os.makedirs(user_upload_dir, exist_ok=True)
    filepath = os.path.join(user_upload_dir, unique_name)
    
    # 保存文件
    file.save(filepath)
    
    # 解析专利信息
    patent_info = PDFParser.parse_pdf(filepath)
    patent_number = request.form.get('patent_number') or patent_info.get('patent_number', '')
    
    # 验证专利号
    is_valid, normalized_num = validate_patent_number(patent_number)
    if not is_valid:
        raise ValueError('无效的专利号格式，请检查后重新输入')

    # 创建数据库记录
    submission = Submission(
        user_id=current_user.id,
        patent_number=normalized_num,
        original_filename=file.filename,
        file_path=filepath,
        title_zh=patent_info.get('title'),
        applicants=json.dumps(patent_info.get('applicants', [])),
        inventors=json.dumps(patent_info.get('inventors', [])),
        application_date=patent_info.get('application_date'),
        publication_date=patent_info.get('publication_date'),
        status='uploaded'
    )
    db.session.add(submission)
    db.session.flush()  # 获取submission.id

    # 保存文件记录
    file_record = File(
        submission_id=submission.id,
        file_type='original',
        file_path=filepath,
        file_format=file_ext,
        file_size=os.path.getsize(filepath)
    )
    db.session.add(file_record)
    db.session.commit()

    # 异步处理任务
    process_uploaded_file.delay(submission.id)

    return {
        'submission': submission,
        'patent_info': patent_info
    }

@upload_bp.route('/api/recent-uploads', methods=['GET'])
@login_required
def recent_uploads():
    """
    获取用户最近上传记录
    ---
    responses:
      200:
        description: 返回最近5条上传记录
    """
    submissions = Submission.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Submission.created_at.desc()
    ).limit(5).all()
    
    return jsonify([{
        'id': s.id,
        'patent_number': s.patent_number,
        'title': s.title_zh or '未命名专利',
        'date': s.created_at.strftime('%Y-%m-%d %H:%M'),
        'status': s.status,
        'url': url_for('main.submission_detail', id=s.id)
    } for s in submissions])