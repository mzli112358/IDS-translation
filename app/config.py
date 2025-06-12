import os
import secrets
from pathlib import Path

class Config:
    # 数据库配置 (直接明文存储，便于开发修改)
    DB_HOST = '115.190.13.176'
    DB_PORT = 3306
    DB_NAME = 'IDS'
    DB_USER = 'mzli112358'
    DB_PASSWORD = 'Limingzhe2004'
    DB_CHARSET = 'utf8mb4'
    
    PER_PAGE_ITEMS = 10  # 每页显示数量
    
    # SQLAlchemy连接URI
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset={DB_CHARSET}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 百度翻译API
    BAIDU_TRANSLATE_APP_ID = '20250611002379660'
    BAIDU_TRANSLATE_SECRET_KEY = 'Khq5O9od1_XoxO7LR0Cb'

    # Flask安全配置
    SECRET_KEY = secrets.token_hex(32)  # 每次重启会变化，生产环境建议固定
    SESSION_COOKIE_SECURE = False       # 开发环境关闭HTTPS
    PERMANENT_SESSION_LIFETIME = 86400  # 会话有效期(秒)

    # 文件上传配置
    UPLOAD_FOLDER = str(Path(__file__).parent / 'static' / 'uploads')
    ALLOWED_EXTENSIONS = {'pdf'}
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB文件大小限制

    # EPO API配置
    EPO_OPS_CONSUMER_KEY = 'p1unq1xQz7OJvst34CQ9KaaVTDqv90hK'
    EPO_OPS_SECRET_KEY = 'qBntzHeGAUL06HHd'
    EPO_OPS_TOKEN_URL = 'https://ops.epo.org/3.2/auth/accesstoken'
    EPO_OPS_API_URL = 'https://ops.epo.org/3.2/rest-services/'
    EPO_REQUEST_TIMEOUT = 30  # API请求超时(秒)

    # 本地开发特殊配置
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True

    @staticmethod
    def init_app(app):
        """应用初始化配置"""
        # 确保上传目录存在
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # 开发模式下允许覆盖配置
        if app.debug:
            app.config['TEMPLATES_AUTO_RELOAD'] = True
            app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0