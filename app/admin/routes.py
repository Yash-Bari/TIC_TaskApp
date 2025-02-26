from flask import render_template, jsonify, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from app.admin import admin_bp
from app.auth.routes import admin_required
from app.models import db, User, Score, Task, Submission
from datetime import datetime
from sqlalchemy import desc

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    users = User.query.all()
    active_students = User.query.filter_by(role='student', is_active=True).all()
    tasks = Task.query.all()
    pending_evaluations = Submission.query.filter_by(status='submitted').all()
    
    return render_template('admin/dashboard.html',
                         users=users,
                         active_students=active_students,
                         tasks=tasks,
                         pending_evaluations=pending_evaluations)

# User Management Routes
@admin_bp.route('/users')
@login_required
@admin_required
def user_list():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        role = request.form.get('role')
        is_active = request.form.get('is_active') == 'true'
        
        if role in ['student', 'coordinator', 'admin']:
            user.role = role
        user.is_active = is_active
        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('admin.user_list'))
    
    return render_template('admin/user_detail.html', user=user)

@admin_bp.route('/users/login-history')
@login_required
@admin_required
def login_history():
    users = User.query.order_by(desc(User.last_login)).all()
    return render_template('admin/login_history.html', users=users)

# System Access Control Routes
@admin_bp.route('/system/access-control')
@login_required
@admin_required
def access_control():
    domains = current_app.config['ALLOWED_DOMAINS']
    coordinator_email = current_app.config['COORDINATOR_EMAIL']
    admin_email = current_app.config['ADMIN_EMAIL']
    return render_template('admin/access_control.html', 
                         domains=domains,
                         coordinator_email=coordinator_email,
                         admin_email=admin_email)

# Leaderboard Control Routes
@admin_bp.route('/leaderboard/control', methods=['GET', 'POST'])
@login_required
@admin_required
def leaderboard_control():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'recalculate':
            # Recalculate all scores
            users = User.query.filter_by(role='student').all()
            current_month = datetime.utcnow().month
            current_year = datetime.utcnow().year
            
            for user in users:
                score = Score.query.filter_by(
                    user_id=user.id,
                    month=current_month,
                    year=current_year
                ).first()
                
                if not score:
                    score = Score(user_id=user.id, month=current_month, year=current_year)
                    db.session.add(score)
                
                # Calculate total score from submissions
                submissions = Submission.query.filter_by(user_id=user.id).all()
                total_score = sum(s.evaluation.total_score for s in submissions if s.evaluation)
                tasks_completed = len([s for s in submissions if s.evaluation])
                
                score.total_score = total_score
                score.tasks_completed = tasks_completed
            
            # Update rankings
            scores = Score.query.filter_by(month=current_month, year=current_year)\
                .order_by(desc(Score.total_score)).all()
            for idx, score in enumerate(scores, 1):
                score.rank = idx
            
            db.session.commit()
            flash('Leaderboard has been recalculated', 'success')
        
        elif action == 'publish':
            # Toggle leaderboard visibility
            current_month = datetime.utcnow().month
            current_year = datetime.utcnow().year
            scores = Score.query.filter_by(month=current_month, year=current_year).all()
            is_published = request.form.get('is_published') == 'true'
            
            for score in scores:
                score.is_published = is_published
            
            db.session.commit()
            status = 'published' if is_published else 'unpublished'
            flash(f'Leaderboard has been {status}', 'success')
    
    return render_template('admin/leaderboard_control.html')
