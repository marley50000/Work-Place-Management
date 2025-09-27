from flask import render_template, url_for, flash, redirect, request, Blueprint, abort
from flask_login import login_user, current_user, logout_user, login_required
from wms import db
import datetime
import os

from wms.models import User, Task, Shift, Attendance, LeaveRequest, Document, Goal, Evaluation, Announcement, Message, Asset, AssetLog
from wms.forms import (RegistrationForm, LoginForm, TaskForm, ShiftForm,
                       LeaveRequestForm, EmptyForm, DocumentForm, GoalForm,
                       EvaluationForm, AnnouncementForm, MessageForm,
                       AssetForm, PayslipUploadForm)  # ← added at the end
from .decorators import roles_required
from werkzeug.utils import secure_filename
from flask import current_app, jsonify
from sqlalchemy import or_
import json
from collections import Counter

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
@main_bp.route("/home")
@login_required
def home():
    tasks = current_user.tasks_assigned_to
    shifts = current_user.shifts
    last_attendance = Attendance.query.filter_by(user_id=current_user.id).order_by(Attendance.clock_in_time.desc()).first()
    attendance_history = Attendance.query.filter_by(user_id=current_user.id).order_by(Attendance.clock_in_time.desc()).limit(7).all()
    leave_requests = current_user.leave_requests
    goals = Goal.query.filter_by(user=current_user).filter(Goal.status != 'Archived').all()
    clock_form = EmptyForm()
    return render_template('index.html', title='Home', tasks=tasks, shifts=shifts, last_attendance=last_attendance, attendance_history=attendance_history, leave_requests=leave_requests, goals=goals, clock_form=clock_form)

@main_bp.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register', form=form)

@main_bp.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@main_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.login'))


@main_bp.route("/task/new", methods=['GET', 'POST'])
@login_required
@roles_required('Admin', 'Manager')
def new_task():
    form = TaskForm()
    if form.validate_on_submit():
        task = Task(title=form.title.data,
                    description=form.description.data,
                    priority=form.priority.data,
                    deadline=form.deadline.data,
                    assigned_to=form.assigned_to.data,
                    assigned_by=current_user)
        db.session.add(task)
        db.session.commit()
        flash('The task has been created!', 'success')
        return redirect(url_for('main.home'))
    return render_template('create_task.html', title='New Task', form=form, legend='New Task')


@main_bp.route("/shift/new", methods=['GET', 'POST'])
@login_required
@roles_required('Admin', 'Manager')
def new_shift():
    form = ShiftForm()
    if form.validate_on_submit():
        shift = Shift(start_time=form.start_time.data,
                      end_time=form.end_time.data,
                      user=form.user.data)
        db.session.add(shift)
        db.session.commit()
        flash('The shift has been created!', 'success')
        return redirect(url_for('main.home'))
    return render_template('create_shift.html', title='New Shift', form=form, legend='New Shift')


@main_bp.route("/attendance/clock", methods=['POST'])
@login_required
def clock_in_out():
    last_attendance = Attendance.query.filter_by(user_id=current_user.id).order_by(Attendance.clock_in_time.desc()).first()

    if last_attendance and last_attendance.clock_out_time is None:
        # Clock out
        last_attendance.clock_out_time = datetime.datetime.utcnow()
        flash('You have been clocked out.', 'success')
    else:
        # Clock in
        new_attendance = Attendance(user_id=current_user.id)
        db.session.add(new_attendance)
        flash('You have been clocked in.', 'success')

    db.session.commit()
    return redirect(url_for('main.home'))


@main_bp.route("/leave/new", methods=['GET', 'POST'])
@login_required
def new_leave_request():
    form = LeaveRequestForm()
    if form.validate_on_submit():
        leave_request = LeaveRequest(start_date=form.start_date.data,
                                     end_date=form.end_date.data,
                                     reason=form.reason.data,
                                     user=current_user)
        db.session.add(leave_request)
        db.session.commit()
        flash('Your leave request has been submitted.', 'success')
        return redirect(url_for('main.home'))
    return render_template('create_leave_request.html', title='New Leave Request', form=form, legend='New Leave Request')


@main_bp.route("/leave/requests")
@login_required
@roles_required('Admin', 'Manager')
def leave_requests():
    requests = LeaveRequest.query.order_by(LeaveRequest.start_date.asc()).all()
    return render_template('leave_requests.html', title='Leave Requests', requests=requests)


@main_bp.route("/leave/requests/<int:request_id>/approve", methods=['POST'])
@login_required
@roles_required('Admin', 'Manager')
def approve_leave_request(request_id):
    leave_request = LeaveRequest.query.get_or_404(request_id)
    leave_request.status = 'Approved'
    db.session.commit()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":     # NEW: Ajax request → JSON
        return jsonify({'status': 'Approved'})
    flash('The leave request has been approved.', 'success')
    return redirect(url_for('main.leave_requests'))

@main_bp.route("/leave/requests/<int:request_id>/reject", methods=['POST'])
@login_required
@roles_required('Admin', 'Manager')
def reject_leave_request(request_id):
    leave_request = LeaveRequest.query.get_or_404(request_id)
    leave_request.status = 'Rejected'
    db.session.commit()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":     # NEW
        return jsonify({'status': 'Rejected'})
    flash('The leave request has been rejected.', 'danger')
    return redirect(url_for('main.leave_requests'))




@main_bp.route("/document/upload", methods=['GET', 'POST'])
@login_required
@roles_required('Admin', 'Manager')
def upload_document():
    form = DocumentForm()
    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)

        # create folder if it doesn’t exist
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)

        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        document = Document(filename=filename,
                            user=form.user.data,
                            category=form.category.data,
                            expiry_date=form.expiry_date.data)
        db.session.add(document)
        db.session.commit()
        flash('The document has been uploaded.', 'success')
        return redirect(url_for('main.documents'))
    return render_template('upload_document.html', title='Upload Document', form=form)


@main_bp.route("/documents")
@login_required
@roles_required('Admin', 'Manager')
def documents():
    query = request.args.get('q')
    if query:
        docs = Document.query.filter(Document.filename.contains(query)).all()
    else:
        docs = Document.query.all()
    return render_template('documents.html', title='Document Management', documents=docs, today=datetime.date.today())


@main_bp.route("/my_payslips")
@login_required
def my_payslips():
    payslips = Document.query.filter_by(user=current_user, category='Payslip').order_by(Document.upload_date.desc()).all()
    return render_template('my_payslips.html', title='My Payslips', payslips=payslips)


@main_bp.route("/analytics")
@login_required
@roles_required('Admin', 'Manager')
def analytics():
    # Calculate total hours worked by each employee
    users = User.query.all()
    attendance_data = {}
    for user in users:
        total_duration = datetime.timedelta(0)
        records = Attendance.query.filter_by(user_id=user.id).all()
        for record in records:
            if record.clock_in_time and record.clock_out_time:
                total_duration += record.clock_out_time - record.clock_in_time
        attendance_data[user.username] = total_duration.total_seconds() / 3600

    chart_data = {
        'labels': list(attendance_data.keys()),
        'data': list(attendance_data.values()),
    }

    return render_template('analytics.html', title='Analytics Dashboard', chart_data=json.dumps(chart_data))


@main_bp.route("/goal/new", methods=['GET', 'POST'])
@login_required
def new_goal():
    form = GoalForm()
    if form.validate_on_submit():
        goal = Goal(title=form.title.data,
                    description=form.description.data,
                    status=form.status.data,
                    user=current_user)
        db.session.add(goal)
        db.session.commit()
        flash('Your goal has been created.', 'success')
        return redirect(url_for('main.home'))
    return render_template('create_goal.html', title='New Goal', form=form)


@main_bp.route("/goal/<int:goal_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    if goal.user != current_user and current_user.role not in ['Admin', 'Manager']:
        abort(403)

    form = GoalForm(obj=goal)
    if form.validate_on_submit():
        goal.title = form.title.data
        goal.description = form.description.data
        goal.status = form.status.data
        db.session.commit()
        flash('Your goal has been updated.', 'success')
        return redirect(url_for('main.home'))

    return render_template('create_goal.html', title='Edit Goal', form=form)


@main_bp.route("/evaluation/new/<int:employee_id>", methods=['GET', 'POST'])
@login_required
@roles_required('Admin', 'Manager')
def new_evaluation(employee_id):
    employee = User.query.get_or_404(employee_id)
    form = EvaluationForm()
    if form.validate_on_submit():
        evaluation = Evaluation(content=form.content.data,
                                rating=form.rating.data,
                                author=current_user,
                                employee=employee)
        db.session.add(evaluation)
        db.session.commit()
        flash(f"Evaluation for {employee.username} has been submitted.", 'success')
        return redirect(url_for('main.home'))
    return render_template('create_evaluation.html', title='New Evaluation', form=form, employee=employee)


@main_bp.route("/evaluations/<int:user_id>")
@login_required
def view_evaluations(user_id):
    user = User.query.get_or_404(user_id)
    if user != current_user and current_user.role not in ['Admin', 'Manager']:
        abort(403)

    evaluations = user.evaluations_received

    # Calculate statistics for visualizations
    ratings = [e.rating for e in evaluations]
    average_rating = sum(ratings) / len(ratings) if ratings else 0

    # For pie chart: distribution of ratings
    rating_counts = Counter(ratings)
    rating_labels = [str(i) for i in range(1, 6)]
    rating_data = [rating_counts[i] for i in range(1, 6)]

    return render_template('view_evaluations.html',
                           title='View Evaluations',
                           user=user,
                           evaluations=evaluations,
                           average_rating=f"{average_rating:.2f}",
                           rating_labels=json.dumps(rating_labels),
                           rating_data=json.dumps(rating_data))


@main_bp.route("/announcements")
@login_required
def announcements():
    all_announcements = Announcement.query.order_by(Announcement.date_posted.desc()).all()
    return render_template('announcements.html', title='Announcements', announcements=all_announcements)


UPLOAD_FOLDER = 'c:\\Users\\Spark Marley\\Desktop\\julies-try 3\\wms\\static\\uploads'
ANNOUNCEMENT_FOLDER = os.path.join(UPLOAD_FOLDER, 'announcements')
if not os.path.exists(ANNOUNCEMENT_FOLDER):
    os.makedirs(ANNOUNCEMENT_FOLDER)

def save_announcement_media(media_file, media_type):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(media_file.filename)
    media_filename = random_hex + f_ext
    media_path = os.path.join(ANNOUNCEMENT_FOLDER, media_filename)

    if media_type == 'image':
        output_size = (1250, 750) # Resize image for consistency
        i = Image.open(media_file)
        i.thumbnail(output_size)
        i.save(media_path)
    elif media_type == 'video':
        media_file.save(media_path) # Save video directly
    return media_filename

@main_bp.route("/announcement/new", methods=['GET', 'POST'])
@login_required
@roles_required('Admin', 'Manager')
def new_announcement():
    form = AnnouncementForm()
    if form.validate_on_submit():
        image_file = None
        video_file = None

        if form.image.data:
            image_file = save_announcement_media(form.image.data, 'image')
        if form.video.data:
            video_file = save_announcement_media(form.video.data, 'video')

        announcement = Announcement(title=form.title.data,
                                    content=form.content.data,
                                    user=current_user,
                                    image_file=image_file,
                                    video_file=video_file)
        db.session.add(announcement)
        db.session.commit()
        flash('Your announcement has been posted.', 'success')
        return redirect(url_for('main.announcements'))
    return render_template('create_announcement.html', title='New Announcement', form=form)

@main_bp.route("/announcement/<int:announcement_id>/delete", methods=['POST'])
@login_required
@roles_required('Admin', 'Manager')
def delete_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    db.session.delete(announcement)
    db.session.commit()
    flash('The announcement has been deleted.', 'success')
    return redirect(url_for('main.announcements'))


@main_bp.route("/messages")
@login_required
def messages():
    # Get all users the current user has had a conversation with
    sent_to = db.session.query(Message.recipient_id).filter(Message.sender_id == current_user.id)
    received_from = db.session.query(Message.sender_id).filter(Message.recipient_id == current_user.id)
    user_ids_with_conversations = list(set([item[0] for item in sent_to.union(received_from)]))

    conversations = User.query.filter(User.id.in_(user_ids_with_conversations)).all()
    all_users = User.query.filter(User.id != current_user.id).all()

    return render_template('messages.html', title='Messages', conversations=conversations, all_users=all_users)


@main_bp.route("/messages/<int:recipient_id>", methods=['GET', 'POST'])
@login_required
def conversation(recipient_id):
    recipient = User.query.get_or_404(recipient_id)
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(content=form.content.data,
                      sender=current_user,
                      recipient=recipient)
        db.session.add(msg)
        db.session.commit()
        return redirect(url_for('main.conversation', recipient_id=recipient_id))

    messages = Message.query.filter(
        or_(
            (Message.sender_id == current_user.id) & (Message.recipient_id == recipient_id),
            (Message.sender_id == recipient_id) & (Message.recipient_id == current_user.id)
        )
    ).order_by(Message.timestamp.asc()).all()

    return render_template('conversation.html', title=f"Conversation with {recipient.username}", form=form, recipient=recipient, messages=messages)


@main_bp.route("/assets")
@login_required
@roles_required('Admin', 'Manager')
def assets():
    all_assets = Asset.query.all()
    form = EmptyForm()
    return render_template('assets.html', title='Asset Management', assets=all_assets, form=form)


@main_bp.route("/asset/new", methods=['GET', 'POST'])
@login_required
@roles_required('Admin', 'Manager')
def new_asset():
    form = AssetForm()
    if form.validate_on_submit():
        asset = Asset(name=form.name.data,
                      description=form.description.data)
        db.session.add(asset)
        db.session.commit()
        flash('The asset has been added.', 'success')
        return redirect(url_for('main.assets'))
    return render_template('create_asset.html', title='New Asset', form=form)


@main_bp.route("/asset/<int:asset_id>/checkout", methods=['POST'])
@login_required
def checkout_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    if asset.status != 'Available':
        flash('This asset is not available to be checked out.', 'danger')
    else:
        asset.status = 'Checked Out'
        asset_log = AssetLog(user=current_user, asset=asset)
        db.session.add(asset_log)
        db.session.commit()
        flash(f"You have checked out {asset.name}.", 'success')
    return redirect(url_for('main.assets'))


@main_bp.route("/asset/<int:asset_id>/checkin", methods=['POST'])
@login_required
def checkin_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    asset_log = AssetLog.query.filter_by(asset_id=asset.id, check_in_time=None).first()

    if asset.status != 'Checked Out' or not asset_log:
        flash('This asset cannot be checked in.', 'danger')
    else:
        if asset_log.user != current_user and current_user.role not in ['Admin', 'Manager']:
            flash('You can only check in assets that you have checked out.', 'danger')
        else:
            asset.status = 'Available'
            asset_log.check_in_time = datetime.datetime.utcnow()
            db.session.commit()
            flash(f"You have checked in {asset.name}.", 'success')

    return redirect(url_for('main.assets'))


# --- NEW ROUTE -------------------------------------------------------
@main_bp.route("/payslip/upload", methods=['GET', 'POST'])
@login_required
@roles_required('Admin', 'Manager')        # ← NEW guard (access control)
def upload_payslip():
    form = PayslipUploadForm()
    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)

        # create folder if it doesn’t exist
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)

        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        document = Document(filename=filename,
                            user=current_user,
                            category='Payslip')
        db.session.add(document)
        db.session.commit()
        flash('Your payslip has been uploaded.', 'success')
        return redirect(url_for('main.my_payslips'))
    return render_template('upload_payslip.html', title='Upload Payslip', form=form)


@main_bp.route("/my_documents")
@login_required
def my_documents():
    docs = Document.query.\
        filter_by(user=current_user).\
        order_by(Document.upload_date.desc()).all()
    return render_template(
        'my_documents.html',
        title='My Documents',
        docs=docs)


# Add these imports at the top of the file
import os
import secrets
from PIL import Image
from flask import current_app
from wms.models import ProfilePicture
from wms.forms import ProfilePictureForm

# Add this function to save profile pictures
def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/uploads/profile_pics', picture_fn)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(picture_path), exist_ok=True)
    
    # Resize image to save space
    output_size = (150, 150)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    
    return picture_fn

# Add this route for profile picture management
@main_bp.route('/profile/picture', methods=['GET', 'POST'])
@login_required
def profile_picture():
    form = ProfilePictureForm()
    if form.validate_on_submit():
        picture_file = save_picture(form.picture.data)
        
        # Check if user already has a profile picture
        if current_user.profile_picture:
            # Delete old picture file if it exists
            old_picture = current_user.profile_picture.filename
            old_picture_path = os.path.join(current_app.root_path, 'static/uploads/profile_pics', old_picture)
            if os.path.exists(old_picture_path):
                os.remove(old_picture_path)
            
            # Update existing record
            current_user.profile_picture.filename = picture_file
        else:
            # Create new profile picture record
            profile_pic = ProfilePicture(filename=picture_file, user_id=current_user.id)
            db.session.add(profile_pic)
        
        db.session.commit()
        flash('Your profile picture has been updated!', 'success')
        return redirect(url_for('main.profile_picture'))
    
    return render_template('profile_picture.html', title='Profile Picture', form=form)


@main_bp.route("/manage_employees")
@login_required
@roles_required('Admin', 'Manager')
def manage_employees():
    users = User.query.all()
    return render_template('manage_employees.html', title='Manage Employees', users=users)