from wms import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from sqlalchemy import Text, Date


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(50), nullable=False, default='Employee') # Roles: Admin, Manager, Employee
    # Add relationship to profile picture
    profile_picture = db.relationship('ProfilePicture', backref='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


# New model for profile pictures
class ProfilePicture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)

    def __repr__(self):
        return f"ProfilePicture('{self.filename}', user_id: {self.user_id})"


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(Text, nullable=True)
    priority = db.Column(db.String(20), nullable=False, default='Medium')  # Low, Medium, High
    deadline = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='To Do')  # To Do, In Progress, Done
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], backref='tasks_assigned_to')
    assigned_by = db.relationship('User', foreign_keys=[assigned_by_id], backref='tasks_created_by')

    def __repr__(self):
        return f"Task('{self.title}', '{self.status}')"


class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='shifts')

    def __repr__(self):
        return f"Shift('{self.user.username}', '{self.start_time}' to '{self.end_time}')"


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    clock_in_time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    clock_out_time = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='attendances')

    def __repr__(self):
        return f"Attendance('{self.user.username}', '{self.clock_in_time}')"


class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(Date, nullable=False)
    end_date = db.Column(Date, nullable=False)
    reason = db.Column(Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')  # Pending, Approved, Rejected
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='leave_requests')

    def __repr__(self):
        return f"LeaveRequest('{self.user.username}', '{self.start_date}' to '{self.end_date}')"


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False, default='General') # e.g., 'General', 'Payslip', 'Contract'
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    expiry_date = db.Column(db.Date, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='documents')

    def __repr__(self):
        return f"Document('{self.filename}', '{self.user.username}')"


class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='In Progress')  # In Progress, Completed, Archived
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='goals')

    def __repr__(self):
        return f"Goal('{self.title}', '{self.user.username}')"


class Evaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # e.g., 1-5
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    author = db.relationship('User', foreign_keys=[author_id], backref='evaluations_written')
    employee = db.relationship('User', foreign_keys=[employee_id], backref='evaluations_received')

    def __repr__(self):
        return f"Evaluation for '{self.employee.username}' by '{self.author.username}'"


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='announcements')

    def __repr__(self):
        return f"Announcement('{self.title}', '{self.date_posted}')"


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')

    def __repr__(self):
        return f"Message from '{self.sender.username}' to '{self.recipient.username}'"


class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='Available')  # Available, Checked Out, In Maintenance

    def __repr__(self):
        return f"Asset('{self.name}', '{self.status}')"


class AssetLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    check_out_time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    check_in_time = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    user = db.relationship('User', backref='asset_logs')
    asset = db.relationship('Asset', backref='logs')

    def __repr__(self):
        return f"AssetLog('{self.asset.name}', '{self.user.username}', '{self.check_out_time}')"