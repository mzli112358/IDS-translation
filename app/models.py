from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db, login_manager
from sqlalchemy import event
import os

class User(UserMixin, db.Model):
    """用户模型（专利代理人/审查员）"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100))
    title = db.Column(db.String(50))  # 职称/职位
    phone = db.Column(db.String(20))
    email_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    submissions = db.relationship('Submission', back_populates='author', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', back_populates='user')
    
    full_name = db.Column(db.String(50))
    department = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    dingtalk = db.Column(db.String(50))
    last_login = db.Column(db.DateTime)
    last_login_ip = db.Column(db.String(20))
    
    def set_password(self, password):
        """设置密码（自动哈希处理）"""
        self.password_hash = generate_password_hash(
            password,
            method='pbkdf2:sha256',
            salt_length=16
        )
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def get_dashboard_stats(self):
        """获取用户仪表盘统计"""
        return {
            'total_submissions': self.submissions.count(),
            'pending': self.submissions.filter_by(status='uploaded').count(),
            'completed': self.submissions.filter_by(status='completed').count()
        }
        

class Submission(db.Model):
    """专利提交记录"""
    __tablename__ = 'submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    patent_number = db.Column(db.String(50), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)  # 原始文件存储路径
    file_size = db.Column(db.Integer)  # 文件大小（字节）
    
    # 专利元数据
    title_zh = db.Column(db.String(500))
    title_en = db.Column(db.String(500))
    abstract_zh = db.Column(db.Text)
    abstract_en = db.Column(db.Text)
    applicants = db.Column(db.Text)  # JSON存储申请人列表
    inventors = db.Column(db.Text)   # JSON存储发明人列表
    application_date = db.Column(db.Date)
    publication_date = db.Column(db.Date)
    ipc_classes = db.Column(db.String(200))  # 国际专利分类号
    
    # 处理状态
    status = db.Column(db.Enum(
        'uploaded',    # 已上传
        'parsing',     # 解析中
        'parsed',      # 已解析
        'searching',   # 检索中
        'translating', # 翻译中
        'reviewing',   # 审核中
        'completed',   # 已完成
        'failed'       # 处理失败
    ), default='uploaded', nullable=False, index=True)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # 关系
    author = db.relationship('User', back_populates='submissions')
    translations = db.relationship('Translation', back_populates='submission', cascade='all, delete-orphan')
    files = db.relationship('File', back_populates='submission', cascade='all, delete-orphan')
    logs = db.relationship('AuditLog', back_populates='submission')
    
    def get_metadata(self):
        """获取标准化专利元数据"""
        return {
            'patent_number': self.patent_number,
            'title_zh': self.title_zh,
            'title_en': self.title_en,
            'application_date': self.application_date.isoformat() if self.application_date else None,
            'publication_date': self.publication_date.isoformat() if self.publication_date else None
        }
    
    def get_file_info(self):
        """获取文件信息"""
        return {
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'download_url': f'/submissions/{self.id}/download'
        }

class Translation(db.Model):
    """专利翻译记录"""
    __tablename__ = 'translations'
    
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False)
    
    # 翻译内容
    source_text = db.Column(db.Text, nullable=False)
    translated_text = db.Column(db.Text)
    translation_source = db.Column(db.Enum(
        'epo',      # 欧洲专利局
        'baidu',    # 百度翻译
        'google',   # Google翻译
        'manual'    # 人工翻译
    ), nullable=False)
    
    # 质量检查
    grammar_checked = db.Column(db.Boolean, default=False)
    grammar_issues = db.Column(db.Text)  # JSON存储语法问题
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    review_notes = db.Column(db.Text)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    submission = db.relationship('Submission', back_populates='translations')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])

class File(db.Model):
    """文件存储记录（多版本支持）"""
    __tablename__ = 'files'
    
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False)
    
    # 文件属性
    file_type = db.Column(db.Enum(
        'original',     # 原始文件
        'parsed',       # 解析后的文本
        'translated',   # 翻译结果
        'export_pdf',   # 导出的PDF
        'export_docx',  # 导出的Word
        'export_other'  # 其他格式
    ), nullable=False)
    
    file_path = db.Column(db.String(512), nullable=False)
    file_format = db.Column(db.String(10), nullable=False)  # pdf/docx/txt等
    file_size = db.Column(db.Integer)
    version = db.Column(db.Integer, default=1)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    submission = db.relationship('Submission', back_populates='files')

class AuditLog(db.Model):
    """操作审计日志"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'))
    
    # 操作信息
    action = db.Column(db.String(50), nullable=False)  # login/upload/download等
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    details = db.Column(db.Text)  # JSON格式的详细数据
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # 关系
    user = db.relationship('User', back_populates='audit_logs')
    submission = db.relationship('Submission', back_populates='logs')

# 事件监听器
@event.listens_for(Submission, 'after_delete')
def delete_submission_files(mapper, connection, target):
    """删除关联文件"""
    if os.path.exists(target.file_path):
        try:
            os.remove(target.file_path)
        except OSError as e:
            current_app.logger.error(f"删除文件失败: {target.file_path}, 错误: {str(e)}")

@login_manager.user_loader
def load_user(user_id):
    """Flask-Login的用户加载器"""
    return User.query.get(int(user_id))