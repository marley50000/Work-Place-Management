from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField, FloatField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, NumberRange
from wtforms_sqlalchemy.fields import QuerySelectField
from wtforms.fields import DateField, DateTimeField
from flask_wtf.file import FileField, FileAllowed
from wms.models import User, Asset

def user_query():
    return User.query

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class TaskForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    priority = SelectField('Priority', choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')],
                           validators=[DataRequired()])
    deadline = DateTimeField('Deadline', format='%Y-%m-%d %H:%M:%S', validators=[DataRequired()])
    assigned_to = QuerySelectField('Assign To', query_factory=user_query, get_label='username', allow_blank=False,
                                   validators=[DataRequired()])
    submit = SubmitField('Create Task')

class ShiftForm(FlaskForm):
    start_time = DateTimeField('Start Time', format='%Y-%m-%d %H:%M:%S', validators=[DataRequired()])
    end_time = DateTimeField('End Time', format='%Y-%m-%d %H:%M:%S', validators=[DataRequired()])
    user = QuerySelectField('Employee', query_factory=user_query, get_label='username', allow_blank=False,
                            validators=[DataRequired()])
    submit = SubmitField('Create Shift')

class LeaveRequestForm(FlaskForm):
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[DataRequired()])
    reason = TextAreaField('Reason', validators=[DataRequired()])
    submit = SubmitField('Submit Request')

class EmptyForm(FlaskForm):
    pass

class DocumentForm(FlaskForm):
    file = FileField('Document', validators=[DataRequired(), FileAllowed(['pdf', 'doc', 'docx', 'jpg', 'png'])])
    user = QuerySelectField(
        'Employee',
        query_factory=user_query,
        get_label=lambda u: f"{u.username} ({u.email})",   # ← show “username (email)”
        allow_blank=False,
        validators=[DataRequired()])
    category = SelectField('Category', choices=[('General', 'General'), ('Payslip', 'Payslip'), ('Contract', 'Contract')],
                           validators=[DataRequired()])
    expiry_date = DateField('Expiry Date (Optional)', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Upload Document')

class ProfilePictureForm(FlaskForm):
    picture = FileField('Profile Picture', validators=[
        DataRequired(),
        FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')
    ])
    submit = SubmitField('Upload Picture')

# --- add just below -----------------------------------------------
class PayslipUploadForm(FlaskForm):
    file = FileField('Payslip (PDF)',
                     validators=[DataRequired(),
                                 FileAllowed(['pdf'], 'PDF files only!')])
    submit = SubmitField('Upload Payslip')

class GoalForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    status = SelectField('Status', choices=[('In Progress', 'In Progress'), ('Completed', 'Completed'), ('Archived', 'Archived')],
                         validators=[DataRequired()])
    submit = SubmitField('Save Goal')

class EvaluationForm(FlaskForm):
    content = TextAreaField('Evaluation Content', validators=[DataRequired()])
    rating = SelectField('Rating', choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], coerce=int,
                         validators=[DataRequired(), NumberRange(min=1, max=5)])
    submit = SubmitField('Submit Evaluation')

class AnnouncementForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    image = FileField('Upload Image (Optional)', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Images only!'), Optional()])
    video = FileField('Upload Video (Optional)', validators=[FileAllowed(['mp4', 'avi', 'mov', 'webm'], 'Videos only!'), Optional()])
    submit = SubmitField('Post Announcement')

class MessageForm(FlaskForm):
    content = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send')


class AssetForm(FlaskForm):
    name = StringField('Asset Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Save Asset')