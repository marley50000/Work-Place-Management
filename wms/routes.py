from flask import render_template, url_for, flash, redirect, request, Blueprint, abort
from flask_login import login_user, current_user, logout_user, login_required
from wms import db
import datetime
import os

from wms.models import User, Task, Shift, Attendance, LeaveRequest, Document, Goal, Evaluation, Announcement, Message, Asset, AssetLog
from wms.forms import (RegistrationForm, LoginForm, TaskForm, ShiftForm,
                       LeaveRequestForm, EmptyForm, DocumentForm, GoalForm,
                       EvaluationForm, AnnouncementForm, MessageForm,
                       AssetForm, PayslipUploadForm, AdminPasswordResetForm)
from .decorators import roles_required
from werkzeug.utils import secure_filename
from flask import current_app, jsonify
from sqlalchemy import or_
import json

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
@main_bp.route("/home")
@login_required
def home():
    # For admins/managers, show both tasks assigned to them AND tasks they created
    if current_user.role in ['Admin', 'Manager']:
        # Get tasks assigned to the admin/manager
        assigned_tasks = current_user.tasks_assigned_to
        # Get tasks created by the admin/manager
        created_tasks = current_user.tasks_created_by
        # Combine both sets of tasks (avoiding duplicates)
        all_admin_tasks = list(set(assigned_tasks + created_tasks))
        tasks = all_admin_tasks
        print(f"DEBUG: Admin viewing tasks. Assigned: {len(assigned_tasks)}, Created: {len(created_tasks)}, Total: {len(tasks)}")
    else:
        # Regular users only see tasks assigned to them
        tasks = current_user.tasks_assigned_to
    # Get shifts based on user role
    if current_user.role in ['Admin', 'Manager']:
        # Admins and Managers see all shifts
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        # Include shifts from today (allow some buffer for recently created shifts)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        all_shifts = Shift.query.all()
        upcoming_shifts = [shift for shift in all_shifts if shift.start_time >= today_start]
        upcoming_shifts_count = len(upcoming_shifts)
        
        # Debug: Print shift information
        print(f"DEBUG: Admin viewing all shifts. Total shifts: {len(all_shifts)}, Upcoming: {upcoming_shifts_count}")
        print(f"DEBUG: Current time (UTC): {now}")
        print(f"DEBUG: Filter start time: {today_start}")
        for shift in all_shifts[:5]:  # Show first 5 shifts for debugging
            print(f"DEBUG: Shift ID {shift.id}: {shift.user.username} - {shift.start_time} to {shift.end_time}")
    else:
        # Regular users see only their own shifts
        shifts = current_user.shifts
        # Filter to show only upcoming shifts (today and future)
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        # Include shifts from today (allow some buffer for recently created shifts)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        upcoming_shifts = [shift for shift in shifts if shift.start_time >= today_start]
        upcoming_shifts_count = len(upcoming_shifts)
    
    last_attendance = Attendance.query.filter_by(user_id=current_user.id).order_by(Attendance.clock_in_time.desc()).first()
    attendance_history = Attendance.query.filter_by(user_id=current_user.id).order_by(Attendance.clock_in_time.desc()).limit(7).all()
    leave_requests = current_user.leave_requests
    goals = Goal.query.filter_by(user=current_user).filter(Goal.status != 'Archived').all()
    clock_form = EmptyForm()
    return render_template('index.html', title='Home', tasks=tasks, shifts=upcoming_shifts, upcoming_shifts_count=upcoming_shifts_count, last_attendance=last_attendance, attendance_history=attendance_history, leave_requests=leave_requests, goals=goals, clock_form=clock_form)

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
    print(f"DEBUG: new_task route accessed by {current_user.username} with role {current_user.role}")
    print(f"DEBUG: Form validate_on_submit: {form.validate_on_submit()}")
    print(f"DEBUG: Form errors: {form.errors}")
    
    if form.validate_on_submit():
        try:
            task = Task(title=form.title.data,
                        description=form.description.data,
                        priority=form.priority.data,
                        deadline=form.deadline.data,
                        assigned_to=form.assigned_to.data,
                        assigned_by=current_user)
            db.session.add(task)
            db.session.commit()
            flash('The task has been created!', 'success')
            print(f"DEBUG: Task created successfully: {task.title} assigned to {task.assigned_to.username}")
            return redirect(url_for('main.home'))
        except Exception as e:
            print(f"DEBUG: Error creating task: {str(e)}")
            flash(f'Error creating task: {str(e)}', 'danger')
            db.session.rollback()
    
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

    # Get task data by user and status
    task_data = {
        'pending': [],
        'in_progress': [],
        'completed': []
    }
    
    for user in users:
        # Count tasks by status for each user
        pending_count = Task.query.filter_by(assigned_to=user).filter(Task.status == 'Pending').count()
        in_progress_count = Task.query.filter_by(assigned_to=user).filter(Task.status == 'In Progress').count()
        completed_count = Task.query.filter_by(assigned_to=user).filter(Task.status == 'Completed').count()
        
        task_data['pending'].append(pending_count)
        task_data['in_progress'].append(in_progress_count)
        task_data['completed'].append(completed_count)

    chart_data = {
        'labels': list(attendance_data.keys()),
        'data': list(attendance_data.values()),
        'task_data': task_data
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
    return render_template('view_evaluations.html', title='View Evaluations', user=user, evaluations=evaluations)


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
    # Get search query from request args
    search_query = request.args.get('search', '')
    
    # Get all users except current user
    all_users = User.query.filter(User.id != current_user.id).all()
    
    # If search query is provided, filter users
    if search_query:
        all_users = [user for user in all_users if search_query.lower() in user.username.lower() or 
                     (user.email and search_query.lower() in user.email.lower())]
    
    # Get users with whom the current user has conversations
    conversations = User.query.join(Message, 
        ((Message.sender_id == User.id) & (Message.recipient_id == current_user.id)) | 
        ((Message.recipient_id == User.id) & (Message.sender_id == current_user.id))
    ).filter(User.id != current_user.id).distinct().all()
    
    # Get unread messages
    unread_by_user = {}
    for user in conversations:
        unread_count = Message.query.filter_by(sender_id=user.id, recipient_id=current_user.id, read=False).count()
        if unread_count > 0:
            unread_by_user[user.id] = unread_count
    
    return render_template('messages.html', title='Messages', 
                          all_users=all_users, conversations=conversations, 
                          unread_by_user=unread_by_user)


@main_bp.route("/conversation/<int:recipient_id>", methods=['GET', 'POST'])
@login_required
def conversation(recipient_id):
    recipient = User.query.get_or_404(recipient_id)
    form = MessageForm()
    
    if form.validate_on_submit():
        message = Message(content=form.content.data, sender=current_user, recipient=recipient)
        db.session.add(message)
        db.session.commit()
        flash('Your message has been sent.', 'success')
        return redirect(url_for('main.conversation', recipient_id=recipient_id))
    
    # Get all messages between current user and recipient
    sent_messages = Message.query.filter_by(sender=current_user, recipient=recipient).all()
    received_messages = Message.query.filter_by(sender=recipient, recipient=current_user).all()
    
    # Mark received messages as read
    for message in received_messages:
        if not message.read:
            message.read = True
    
    db.session.commit()
    
    # Combine and sort messages by date
    messages = sorted(sent_messages + received_messages, key=lambda x: x.date_sent)
    
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
@roles_required('Admin', 'Manager')        # ← NEW line (access control)
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


# Add this function at the top of the file with other imports
@main_bp.context_processor
def inject_unread_messages_count():
    if current_user.is_authenticated:
        unread_count = Message.query.filter_by(recipient_id=current_user.id, read=False).count()
        return {'unread_messages_count': unread_count}
    return {'unread_messages_count': 0}

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


@main_bp.route("/admin/reset_password", methods=['GET', 'POST'])
@login_required
@roles_required('Admin')
def admin_reset_password():
    form = AdminPasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            user.set_password(form.new_password.data)
            db.session.commit()
            flash(f'Password has been reset for {user.username}', 'success')
            return redirect(url_for('main.home'))
        else:
            flash('User with that email not found', 'danger')
    return render_template('admin_reset_password.html', title='Admin Password Reset', form=form)