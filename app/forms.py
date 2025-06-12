from flask_wtf import FlaskForm
# 在 forms.py 文件开头添加
from app.utils.validators import validate_patent_number
from app.utils.validators import validate_password  # 使用WTForms专用验证器
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    TextAreaField,
    FileField,
    SelectField,
    EmailField
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    EqualTo,
    ValidationError,
    Optional
)
from flask_wtf.file import FileAllowed, FileRequired
from flask import current_app
from app.models import User

class LoginForm(FlaskForm):
    """用户登录表单"""
    username = StringField(
        '用户名',
        validators=[
            DataRequired(message='用户名不能为空'),
            Length(min=4, max=20, message='用户名长度4-20个字符')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '请输入用户名',
            'autofocus': True
        }
    )
    password = PasswordField(
        '密码',
        validators=[
            DataRequired(message='密码不能为空'),
            Length(min=8, max=128, message='密码长度8-128个字符')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '请输入密码'
        }
    )
    remember = BooleanField(
        '记住我',
        render_kw={'class': 'form-check-input'}
    )
    submit = SubmitField(
        '登录',
        render_kw={'class': 'btn btn-primary w-100'}
    )

class RegistrationForm(FlaskForm):
    """用户注册表单"""
    username = StringField(
        '用户名',
        validators=[
            DataRequired(message='用户名不能为空'),
            Length(min=4, max=20, message='用户名长度4-20个字符')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '设置登录用户名'
        }
    )
    email = EmailField(
        '邮箱',
        validators=[
            DataRequired(message='邮箱不能为空'),
            Email(message='无效的邮箱格式'),
            Length(max=120, message='邮箱最长120个字符')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'example@domain.com'
        }
    )
    full_name = StringField(
        '真实姓名',
        validators=[
            DataRequired(message='姓名不能为空'),
            Length(max=50, message='姓名最长50个字符')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '用于证书显示'
        }
    )
    password = PasswordField(
        '密码',
        validators=[
            DataRequired(),
            validate_password  # 替换原有的验证逻辑
        ]
    )
    confirm_password = PasswordField(
        '确认密码',
        validators=[DataRequired(message='请确认密码')],
        render_kw={
            'class': 'form-control',
            'placeholder': '再次输入密码'
        }
    )
    submit = SubmitField(
        '注册',
        render_kw={'class': 'btn btn-success w-100'}
    )

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('该用户名已被注册')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('该邮箱已被注册')

class PatentUploadForm(FlaskForm):
    """专利文件上传表单（优化版）"""
    patent_file = FileField(
        '选择专利文件',
        validators=[
            FileRequired(message='请选择文件'),
            FileAllowed(
                lambda: current_app.config['ALLOWED_EXTENSIONS'],  # 动态获取配置
                message=lambda: f"仅支持{', '.join(current_app.config['ALLOWED_EXTENSIONS'])}格式"
            )
        ],
        render_kw={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx',
            'data-max-size': '50MB'  # 前端提示
        }
    )
    patent_number = StringField(
        '专利号',
        validators=[
            Optional(),
            Length(max=50, message='专利号最长50个字符'),
            validate_patent_number  # 新增专利号格式验证
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '例如：CN202310000123A',
            'pattern': r'^[A-Z]{2}\d+[A-Z]?$',  # 前端初步验证
            'title': '格式：国家代码+数字+字母（如CN1234567A）'
        }
    )
    submit = SubmitField(
        '上传并解析',
        render_kw={
            'class': 'btn btn-primary btn-lg w-100',
            'id': 'upload-submit-btn'
        }
    )

    def validate_patent_file(self, field):
        """自定义文件验证（大小+内容检查）"""
        if field.data:
            # 验证文件大小
            max_size = current_app.config['MAX_CONTENT_LENGTH']
            file_data = field.data
            file_data.seek(0, 2)  # 跳到文件末尾
            file_size = file_data.tell()
            file_data.seek(0)  # 重置指针
            
            if file_size > max_size:
                raise ValidationError(f'文件大小超过{max_size//(1024 * 1024)}MB限制')
            
            # 验证文件内容（示例：PDF文件头）
            if file_data.filename.lower().endswith('.pdf'):
                header = file_data.read(4)
                file_data.seek(0)
                if header != b'%PDF':
                    raise ValidationError('无效的PDF文件格式')

class PatentSearchForm(FlaskForm):
    """专利检索表单"""
    patent_number = StringField(
        '专利号',
        validators=[
            DataRequired(message='请输入专利号'),
            Length(max=50, message='专利号最长50个字符')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '例如：CN109670517A'
        }
    )
    search_type = SelectField(
        '检索类型',
        choices=[
            ('publication', '公开号'),
            ('application', '申请号'),
            ('priority', '优先权号')
        ],
        default='publication',
        render_kw={'class': 'form-select'}
    )
    submit = SubmitField(
        '检索专利',
        render_kw={'class': 'btn btn-primary w-100'}
    )

class PasswordResetRequestForm(FlaskForm):
    """密码重置请求表单"""
    email = EmailField(
        '注册邮箱',
        validators=[
            DataRequired(message='请输入注册邮箱'),
            Email(message='无效的邮箱格式')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '验证账户归属'
        }
    )
    submit = SubmitField(
        '发送重置链接',
        render_kw={'class': 'btn btn-warning w-100'}
    )

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if not user:
            raise ValidationError('该邮箱未注册')

class PasswordResetForm(FlaskForm):
    """密码重置表单"""
    password = PasswordField(
        '新密码',
        validators=[
            DataRequired(message='请输入新密码'),
            Length(min=8, max=128, message='密码长度8-128个字符')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '至少8位，包含大小写和数字'
        }
    )
    confirm_password = PasswordField(
        '确认密码',
        validators=[
            DataRequired(message='请确认密码'),
            EqualTo('password', message='两次密码必须一致')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '再次输入新密码'
        }
    )
    submit = SubmitField(
        '重置密码',
        render_kw={'class': 'btn btn-success w-100'}
    )

class ProfileForm(FlaskForm):
    """用户资料表单"""
    email = EmailField(
        '邮箱',
        validators=[
            DataRequired(message='邮箱不能为空'),
            Email(message='无效的邮箱格式')
        ],
        render_kw={
            'class': 'form-control',
            'readonly': True
        }
    )
    full_name = StringField(
        '姓名',
        validators=[
            Length(max=50, message='姓名最长50个字符')
        ],
        render_kw={
            'class': 'form-control'
        }
    )
    department = StringField(
        '部门',
        validators=[
            Length(max=50, message='部门名称最长50个字符')
        ],
        render_kw={
            'class': 'form-control'
        }
    )
    phone = StringField(
        '联系电话',
        validators=[
            Optional(),
            Length(max=20, message='电话号最长20个字符')
        ],
        render_kw={
            'class': 'form-control'
        }
    )
    dingtalk = StringField(
        '钉钉账号',
        validators=[
            Length(max=50, message='账号最长50个字符')
        ],
        render_kw={
            'class': 'form-control'
        }
    )
    current_password = PasswordField(
        '当前密码',
        validators=[
            DataRequired(message='需要验证当前密码')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '修改信息需验证密码'
        }
    )
    submit = SubmitField(
        '保存更改',
        render_kw={
            'class': 'btn btn-primary'
        }
    )
    
    
class ChangePasswordForm(FlaskForm):
    """修改密码表单"""
    current_password = PasswordField(
        '当前密码',
        validators=[
            DataRequired(message='必须输入当前密码')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '请输入当前密码',
            'autocomplete': 'current-password'
        }
    )
    new_password = PasswordField(
        '新密码',
        validators=[
            DataRequired(message='必须输入新密码'),
            Length(min=8, max=128, message='密码长度8-128个字符'),
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '至少8位，包含大小写和数字',
            'pattern': r'(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}',
            'autocomplete': 'new-password'
        }
    )
    confirm_password = PasswordField(
        '确认密码',
        validators=[
            DataRequired(message='请确认新密码'),
            EqualTo('new_password', message='两次密码必须一致')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '再次输入新密码',
            'autocomplete': 'new-password'
        }
    )
    submit = SubmitField(
        '确认修改',
        render_kw={
            'class': 'btn btn-primary w-100'
        }
    )

    def validate_current_password(self, field):
        if not current_user.verify_password(field.data):
            raise ValidationError('当前密码错误')