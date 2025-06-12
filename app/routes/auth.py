from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app import db
from app.forms import LoginForm, RegistrationForm
#from app.services.email import send_verification_email

def send_verification_email(user, token):
    current_app.logger.warning(f"验证邮件未发送（待实现）Token: {token}")
    
    
try:
    from ..utils.validators import validate_password_strength
except ImportError:
    from app.utils.validators import validate_password_strength
    
    
auth_bp = Blueprint('auth', __name__, template_folder='templates/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if not user or not check_password_hash(user.password_hash, form.password.data):
            flash('无效的用户名或密码', 'danger')
            return redirect(url_for('auth.login'))
            
        login_user(user, remember=form.remember.data)
        
        # 记录登录日志
        user.update_last_login()
        db.session.commit()
        
        next_page = request.args.get('next')
        return redirect(next_page or url_for('main.home'))

    return render_template('login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # 密码强度验证
        if not validate_password_strength(form.password.data):
            flash('密码必须包含大小写字母、数字和特殊字符，且长度至少8位', 'warning')
            return redirect(url_for('auth.register'))
            
        # 检查用户名和邮箱唯一性
        if User.query.filter_by(username=form.username.data).first():
            flash('该用户名已被注册', 'danger')
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(email=form.email.data).first():
            flash('该邮箱已被注册', 'danger')
            return redirect(url_for('auth.register'))

        # 创建用户
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            full_name=form.full_name.data
        )
        db.session.add(user)
        db.session.commit()
        
        # 发送验证邮件
        if not app.config['TESTING']:
            send_verification_email(user)
        
        flash('注册成功！请检查邮箱完成验证', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功退出登录', 'info')
    return redirect(url_for('main.home'))

@auth_bp.route('/verify/<token>')
def verify_email(token):
    user = User.verify_email_token(token)
    if not user:
        flash('验证链接无效或已过期', 'danger')
        return redirect(url_for('auth.login'))
    
    if user.email_verified:
        flash('邮箱已验证，无需重复操作', 'info')
    else:
        user.email_verified = True
        db.session.commit()
        flash('邮箱验证成功！', 'success')
    
    return redirect(url_for('main.home'))