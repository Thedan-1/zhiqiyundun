# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, URL # 导入 URL 验证器
from models import User, Role, SystemSetting, ExternalLink # 导入 ExternalLink

class RegistrationForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    confirm_password = PasswordField('确认密码', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('注册')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('该用户名已被使用。请选择其他用户名。')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('该邮箱已被注册。请选择其他邮箱。')

class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember = BooleanField('记住我')
    submit = SubmitField('登录')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('新密码', validators=[DataRequired()])
    confirm_password = PasswordField('确认新密码', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('重置密码')

class UserForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    role = SelectField('角色', coerce=int, validators=[DataRequired()])
    is_active = BooleanField('是否活跃')
    submit = SubmitField('保存')

    def __init__(self, original_username=None, original_email=None, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email
        self.role.choices = [(role.id, role.name) for role in Role.query.order_by('name').all()]

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('该用户名已被使用。请选择其他用户名。')

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('该邮箱已被注册。请选择其他邮箱。')

class RoleForm(FlaskForm):
    name = StringField('角色名称', validators=[DataRequired(), Length(min=2, max=80)])
    description = TextAreaField('描述', validators=[Length(max=255)])
    submit = SubmitField('保存')

    def __init__(self, original_name=None, *args, **kwargs):
        super(RoleForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        if name.data != self.original_name:
            role = Role.query.filter_by(name=name.data).first()
            if role:
                raise ValidationError('该角色名称已被使用。')

class SystemSettingForm(FlaskForm):
    key = StringField('设置键', validators=[DataRequired(), Length(min=2, max=100)])
    value = TextAreaField('设置值', validators=[DataRequired()])
    description = TextAreaField('描述', validators=[Length(max=255)])
    submit = SubmitField('保存')

    def __init__(self, original_key=None, *args, **kwargs):
        super(SystemSettingForm, self).__init__(*args, **kwargs)
        self.original_key = original_key

    def validate_key(self, key):
        if key.data != self.original_key:
            setting = SystemSetting.query.filter_by(key=key.data).first()
            if setting:
                raise ValidationError('该设置键已被使用。')

class ExternalLinkForm(FlaskForm):
    name = StringField('平台名称', validators=[DataRequired(), Length(min=2, max=100)])
    url = StringField('链接地址', validators=[DataRequired(), URL(), Length(max=500)]) # Added URL validator
    description = TextAreaField('描述', validators=[Length(max=255)])
    category = SelectField('分类', validators=[DataRequired()]) # Added category
    icon = StringField('图标 (文件名或FontAwesome类)', validators=[Length(max=100)], default='fas fa-link') # Increased length for icon
    is_active = BooleanField('是否活跃')
    submit = SubmitField('保存')

    def __init__(self, *args, **kwargs):
        super(ExternalLinkForm, self).__init__(*args, **kwargs)
        # 预设一些分类选项，实际应用中可以从数据库或配置中加载
        self.category.choices = [
            ('项目管理和协作工具', '项目管理和协作工具'),
            ('文档管理和网盘工具', '文档管理和网盘工具'),
            ('下载和多媒体工具', '下载和多媒体工具'),
            ('设计和营销小工具', '设计和营销小工具'),
            ('HR工具', 'HR工具'),
            ('财务管理和报销平台', '财务管理和报销平台'),
            ('法律咨询平台', '法律咨询平台'),
            ('国家政策查询平台', '国家政策查询平台'),
            ('一站式中小企业服务平台', '一站式中小企业服务平台'),
            ('其他', '其他')
        ]