from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_caching import Cache

# 创建扩展实例（未初始化）
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
cache = Cache()

# 扩展配置函数
def configure_extensions(app):
    """初始化所有扩展"""
    
    # 数据库扩展
    db.init_app(app)
    migrate.init_app(app, db)
    
    # 登录管理
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # 邮件系统
    mail.init_app(app)
    
    # 缓存系统
    cache.init_app(app, config={
        'CACHE_TYPE': 'redis',
        'CACHE_REDIS_URL': app.config['REDIS_URL']
    })
    
    # 注册自定义扩展
    if app.config.get('CUSTOM_EXTENSION_ENABLED'):
        from .custom import CustomExtension
        custom_ext = CustomExtension()
        custom_ext.init_app(app)