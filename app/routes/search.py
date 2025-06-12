from flask import (
    Blueprint, 
    request, 
    jsonify, 
    render_template, 
    flash, 
    redirect, 
    url_for,
    current_app
)
from flask_login import login_required, current_user
from datetime import datetime
import json
from typing import Dict, Optional

from app.models import Submission, File
from app.utils.epo_api import EPOAPI
from app.utils.validators import validate_patent_number
from app import db
#from app.services.translation import translation_service
# 临时替换为
translation_service = None  # 或任意占位对象
from app.utils.file_processor import save_api_response

search_bp = Blueprint('search', __name__, template_folder='templates')

@search_bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """专利检索主入口"""
    if request.method == 'POST':
        return _handle_search_request()
    return render_template('search/search.html')

@search_bp.route('/api/search', methods=['GET'])
@login_required
def api_search():
    """
    AJAX专利搜索API
    ---
    tags:
      - Search
    parameters:
      - name: number
        in: query
        type: string
        required: true
        description: 专利号 (如 CN109670517A)
    responses:
      200:
        description: 专利数据
      400:
        description: 无效请求
      500:
        description: 服务器错误
    """
    patent_number = request.args.get('number')
    if not patent_number:
        return jsonify({'error': '专利号不能为空'}), 400

    try:
        is_valid, normalized_num = validate_patent_number(patent_number)
        if not is_valid:
            return jsonify({'error': '无效的专利号格式'}), 400

        data = _fetch_patent_data(normalized_num)
        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f"API搜索失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

def _handle_search_request():
    """处理搜索表单提交"""
    patent_number = request.form.get('patent_number').strip()
    is_valid, normalized_num = validate_patent_number(patent_number)
    
    if not is_valid:
        flash('无效的专利号格式', 'danger')
        return redirect(url_for('search.search'))

    # 检查是否已存在
    existing = Submission.query.filter_by(
        patent_number=normalized_num,
        user_id=current_user.id
    ).first()
    
    if existing:
        flash('该专利已存在您的提交记录中', 'info')
        return redirect(url_for('main.submission_detail', id=existing.id))

    try:
        # 获取专利数据
        patent_data = _fetch_patent_data(normalized_num)
        
        # 创建提交记录
        submission = _create_submission_record(normalized_num, patent_data)
        
        # 保存API原始数据
        file_path = save_api_response(
            data=patent_data,
            filename=f"{normalized_num}.json",
            user_id=current_user.id
        )
        
        # 创建文件记录
        file_record = File(
            submission_id=submission.id,
            file_type='original',
            file_path=file_path,
            file_format='json'
        )
        db.session.add(file_record)
        db.session.commit()

        flash(f'成功检索专利: {normalized_num}', 'success')
        return redirect(url_for('main.submission_detail', id=submission.id))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"专利检索失败: {str(e)}", exc_info=True)
        flash(f'检索失败: {str(e)}', 'danger')
        return redirect(url_for('search.search'))

def _fetch_patent_data(patent_number: str) -> Dict:
    """获取专利数据（带缓存检查）"""
    # 尝试从EPO获取完整数据
    data = EPOAPI.search_patent(patent_number)
    
    # 自动获取英文翻译（如果原始数据是中文）
    if 'title_zh' in data and not data.get('title_en'):
        data['title_en'], _ = translation_service.translate_patent_text(
            data['title_zh'],
            patent_number
        )
    
    return {
        'patent_number': patent_number,
        'title_zh': data.get('title_zh'),
        'title_en': data.get('title_en'),
        'abstract_zh': data.get('abstract_zh'),
        'abstract_en': data.get('abstract_en'),
        'applicants': data.get('applicants', []),
        'inventors': data.get('inventors', []),
        'application_date': data.get('application_date'),
        'publication_date': data.get('publication_date'),
        'ipc_classes': data.get('ipc_classes', []),
        'source': 'epo'
    }

def _create_submission_record(
    patent_number: str, 
    patent_data: Dict
) -> Submission:
    """创建新的提交记录"""
    submission = Submission(
        user_id=current_user.id,
        patent_number=patent_number,
        original_filename=f"{patent_number}.json",
        file_path='',  # 由File模型单独处理
        title_zh=patent_data.get('title_zh'),
        title_en=patent_data.get('title_en'),
        applicants=json.dumps(patent_data.get('applicants', [])),
        inventors=json.dumps(patent_data.get('inventors', [])),
        application_date=patent_data.get('application_date'),
        publication_date=patent_data.get('publication_date'),
        ipc_classes=','.join(patent_data.get('ipc_classes', [])),
        status='parsed'
    )
    db.session.add(submission)
    db.session.commit()
    return submission

@search_bp.route('/api/recent-searches', methods=['GET'])
@login_required
def recent_searches():
    """获取最近搜索记录"""
    recent = Submission.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Submission.created_at.desc()
    ).limit(5).all()
    
    return jsonify([{
        'id': s.id,
        'patent_number': s.patent_number,
        'title': s.title_en or s.title_zh,
        'date': s.created_at.isoformat()
    } for s in recent])