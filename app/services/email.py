from flask import current_app
from flask_mail import Message
from threading import Thread
from app.extensions import mail

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_verification_email(user, token):
    """发送验证邮件的核心实现"""
    msg = Message(
        subject="IDS系统 - 邮箱验证",
        recipients=[user.email],
        sender=current_app.config['MAIL_DEFAULT_SENDER']
    )
    msg.body = f"""请点击以下链接验证您的邮箱：
{url_for('auth.verify_email', token=token, _external=True)}

如非本人操作请忽略此邮件"""
    
    # 异步发送
    Thread(
        target=send_async_email,
        args=(current_app._get_current_object(), msg)
    ).start()