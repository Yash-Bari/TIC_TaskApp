from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import login_required, current_user
from app.student import student_bp
from app.models import Task, Submission, Notification, Score, User, db
from sqlalchemy import func
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, URLField, SelectField
from wtforms.validators import DataRequired, URL, Optional

class SubmissionForm(FlaskForm):
    submission_url = URLField('GitHub Repository URL', validators=[
        DataRequired(),
        URL(message='Please provide a valid URL')
    ])
    live_demo_url = URLField('Live Demo URL (Optional)', validators=[
        Optional(),
        URL(message='Please provide a valid URL')
    ])
    comments = TextAreaField('Additional Comments')

@student_bp.route('/dashboard')
@login_required
def dashboard():
    # Get all tasks assigned to the student
    tasks = Task.query.filter_by(is_active=True).all()
    
    # Get submissions for the current user
    submissions = Submission.query.filter_by(user_id=current_user.id).all()
    submitted_task_ids = [s.task_id for s in submissions]
    
    # Categorize tasks
    pending_tasks = [t for t in tasks if t.id not in submitted_task_ids]
    submitted_tasks = [s for s in submissions if not s.evaluation]
    evaluated_tasks = [s for s in submissions if s.evaluation]
    
    # Get user's notifications
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Notification.created_at.desc()
    ).limit(10).all()
    
    unread_notifications = [n for n in notifications if not n.is_read]
    
    # Get user's performance metrics
    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year
    
    score = Score.query.filter_by(
        user_id=current_user.id,
        month=current_month,
        year=current_year
    ).first()
    
    if not score:
        score = Score(
            user_id=current_user.id,
            month=current_month,
            year=current_year,
            total_score=0,
            tasks_completed=0
        )
        db.session.add(score)
        db.session.commit()
    
    # Calculate current rank
    rankings = db.session.query(
        Score.user_id,
        func.rank().over(
            order_by=Score.total_score.desc()
        ).label('rank')
    ).filter_by(
        month=current_month,
        year=current_year
    ).all()
    
    current_rank = next(
        (rank for user_id, rank in rankings if user_id == current_user.id),
        len(rankings)
    )
    
    return render_template('student/dashboard.html',
        tasks=tasks,
        pending_tasks=pending_tasks,
        submitted_tasks=submitted_tasks,
        evaluated_tasks=evaluated_tasks,
        notifications=notifications,
        unread_notifications=unread_notifications,
        current_rank=current_rank,
        total_score=score.total_score,
        tasks_completed=score.tasks_completed
    )

@student_bp.route('/task/<int:task_id>')
@login_required
def view_task(task_id):
    task = Task.query.get_or_404(task_id)
    submission = Submission.query.filter_by(
        task_id=task_id,
        user_id=current_user.id
    ).first()
    
    return render_template('student/view_task.html',
        task=task,
        submission=submission,
        now=datetime.utcnow()
    )

@student_bp.route('/task/<int:task_id>/submit', methods=['GET', 'POST'])
@login_required
def submit_task(task_id):
    task = Task.query.get_or_404(task_id)
    form = SubmissionForm()
    
    # Check if task is still accepting submissions
    if datetime.utcnow() > task.deadline:
        flash('This task is past its deadline and no longer accepts submissions.', 'error')
        return redirect(url_for('student.view_task', task_id=task_id))
    
    # Check if already submitted
    existing_submission = Submission.query.filter_by(
        task_id=task_id,
        user_id=current_user.id
    ).first()
    
    if existing_submission:
        flash('You have already submitted this task.', 'info')
        return redirect(url_for('student.view_task', task_id=task_id))
    
    if form.validate_on_submit():
        # Create submission
        submission = Submission(
            task_id=task_id,
            user_id=current_user.id,
            submission_url=form.submission_url.data,
            live_demo_url=form.live_demo_url.data if form.live_demo_url.data else None,
            status='submitted'
        )
        db.session.add(submission)
        
        # Create notification for student
        notification = Notification(
            user_id=current_user.id,
            title=f'Task Submitted: {task.title}',
            message=f'Your submission for {task.title} has been received and is pending evaluation.',
            type='submission_received'
        )
        db.session.add(notification)
        
        # Create notification for coordinator
        coordinator_notification = Notification(
            user_id=task.created_by,
            title=f'New Submission: {task.title}',
            message=f'A new submission for {task.title} has been received from {current_user.name}.',
            type='new_submission'
        )
        db.session.add(coordinator_notification)
        
        try:
            db.session.commit()
            flash('Your submission has been recorded successfully! You will be notified when it is evaluated.', 'success')
            return redirect(url_for('student.view_task', task_id=task_id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error recording submission: {str(e)}')
            flash('An error occurred while recording your submission. Please try again.', 'error')
    
    return render_template('student/submit_task.html',
        task=task,
        form=form
    )

@student_bp.route('/notifications')
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Notification.created_at.desc()
    ).paginate(
        page=page,
        per_page=20,
        error_out=False
    )
    
    # Mark notifications as read
    unread = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).all()
    
    for notification in unread:
        notification.is_read = True
    
    db.session.commit()
    
    return render_template('student/notifications.html',
        notifications=notifications
    )
