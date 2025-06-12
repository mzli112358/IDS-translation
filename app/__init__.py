import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

# 初始化扩展（不依赖app实例）
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

def create_app(config_class):
    """
    应用工厂函数
    :param config_class: 配置类（如Config）
    :return: Flask应用实例
    """
    # 创建应用实例
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    
    # 加载配置
    app.config.from_object(config_class)
    
    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # 初始化扩展
    initialize_extensions(app)
    
    # 注册蓝图
    register_blueprints(app)
    
    # 配置错误处理器
    register_error_handlers(app)
    
    return app

def initialize_extensions(app):
    """初始化所有扩展"""
    db.init_app(app)
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请登录以访问此页面'
    login_manager.login_message_category = 'warning'
    
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    # 注册上下文处理器
    @app.context_processor
    def inject_template_vars():
        return dict(
            debug_mode=app.debug,
            app_name="IDS翻译系统"
        )

def register_blueprints(app):
    """注册所有蓝图（延迟导入避免循环依赖）"""
    with app.app_context():
        # 认证相关路由
        from app.routes.auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
        
        # 主功能路由
        from app.routes.main import main_bp
        app.register_blueprint(main_bp)
        
        # 文件上传路由
        from app.routes.upload import upload_bp
        app.register_blueprint(upload_bp)
        
        # 专利搜索路由
        from app.routes.search import search_bp
        app.register_blueprint(search_bp)
        
        # API路由（如需）
        from app.routes.api import api_bp
        app.register_blueprint(api_bp, url_prefix='/api')

def register_error_handlers(app):
    """注册全局错误处理器"""
    from flask import render_template
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500