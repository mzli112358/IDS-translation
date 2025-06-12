from flask import (
    Blueprint, 
    render_template, 
    request, 
    redirect, 
    url_for, 
    flash, 
    abort,
    current_app
)
from flask_login import login_required, current_user
from flask_paginate import Pagination, get_page_parameter
from werkzeug.utils import secure_filename
import os
from datetime import datetime

from app.models import Submission, User
from app.forms import ProfileForm, ChangePasswordForm
from app import db
from app.utils.validators import validate_file_extension
from app.services.translation import generate_translation_preview

main_bp = Blueprint('main', __name__, template_folder='templates/main')

@main_bp.route('/')
def home():
    """系统首页"""
    if current_user.is_authenticated:
        recent_submissions = current_user.submissions \
            .order_by(Submission.created_at.desc()) \
            .limit(3) \
            .all()
        return render_template('home.html', recent_submissions=recent_submissions)
    return render_template('home.html')

@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """用户资料编辑"""
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        try:
            # 密码验证
            if not current_user.check_password(form.current_password.data):
                flash('当前密码验证失败', 'danger')
                return redirect(url_for('main.profile'))
                
            # 更新资料
            form.populate_obj(current_user)
            current_user.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash('个人资料已更新', 'success')
            return redirect(url_for('main.profile'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"更新资料失败: {str(e)}")
            flash('资料更新失败，请稍后重试', 'danger')
    
    return render_template('profile.html', form=form)

@main_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """修改密码"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        try:
            # 验证当前密码
            if not current_user.check_password(form.current_password.data):
                flash('当前密码错误', 'danger')
                return redirect(url_for('main.change_password'))
                
            # 设置新密码
            current_user.set_password(form.new_password.data)
            current_user.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash('密码已成功更新', 'success')
            return redirect(url_for('main.profile'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"密码修改失败: {str(e)}")
            flash('密码修改失败，请稍后重试', 'danger')
    
    return render_template('change_password.html', form=form)

@main_bp.route('/submissions')
@login_required
def submissions():
    """用户提交记录列表"""
    # 分页参数
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = current_app.config.get('PER_PAGE_ITEMS', 10)
    
    # 查询构建
    query = current_user.submissions.order_by(Submission.created_at.desc())
    total = query.count()
    
    # 分页数据
    pagination = Pagination(
        page=page,
        per_page=per_page,
        total=total,
        css_framework='bootstrap4',
        record_name='submissions'
    )
    
    submissions_page = query.paginate(page=page, per_page=per_page)
    
    return render_template(
        'submissions.html',
        submissions=submissions_page.items,
        pagination=pagination
    )

@main_bp.route('/submissions/<int:submission_id>')
@login_required
def submission_detail(submission_id):
    """提交详情页"""
    submission = Submission.query.get_or_404(submission_id)
    
    # 权限验证
    if submission.user_id != current_user.id:
        current_app.logger.warning(
            f"用户 {current_user.id} 尝试访问未授权的提交 {submission_id}"
        )
        abort(403)
    
    # 生成翻译预览
    translation_preview = generate_translation_preview(submission)
    
    return render_template(
        'submission_detail.html',
        submission=submission,
        translation=translation_preview
    )

@main_bp.route('/submissions/<int:submission_id>/delete', methods=['POST'])
@login_required
def delete_submission(submission_id):
    """删除提交记录"""
    submission = Submission.query.get_or_404(submission_id)
    
    # 权限验证
    if submission.user_id != current_user.id:
        abort(403)
    
    try:
        # 删除关联文件
        if os.path.exists(submission.file_path):
            os.remove(submission.file_path)
        
        # 删除数据库记录
        db.session.delete(submission)
        db.session.commit()
        
        flash('提交记录已删除', 'success')
        return redirect(url_for('main.submissions'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除提交失败: {str(e)}")
        flash('删除失败，请稍后重试', 'danger')
        return redirect(url_for('main.submission_detail', submission_id=submission_id))

@main_bp.route('/submissions/<int:submission_id>/download')
@login_required
def download_submission(submission_id):
    """下载提交文件"""
    submission = Submission.query.get_or_404(submission_id)
    
    if submission.user_id != current_user.id:
        abort(403)
    
    if not os.path.exists(submission.file_path):
        flash('文件不存在或已被删除', 'danger')
        return redirect(url_for('main.submissions'))
    
    return send_from_directory(
        directory=os.path.dirname(submission.file_path),
        path=os.path.basename(submission.file_path),
        as_attachment=True,
        download_name=f"IDS_{submission.patent_number or submission.id}.pdf"
    )
    
@main_bp.route('/api/recent-activities')
@login_required
def recent_activities():
    """获取用户最近活动"""
    searches = Submission.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Submission.created_at.desc()
    ).limit(5).all()

    return jsonify([{
        'type': 'search' if s.file_path else 'upload',
        'title': s.title or s.patent_number,
        'description': f"专利号: {s.patent_number}",
        'time': s.created_at.strftime('%m-%d %H:%M'),
        'link': url_for('main.submission_detail', id=s.id)
    } for s in searches])
    
@main_bp.route('/submissions/delete', methods=['POST'])
@login_required
def delete_submissions():
    data = request.get_json()
    Submission.query.filter(
        Submission.id.in_(data['ids']),
        Submission.user_id == current_user.id
    ).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'success': True})