from flask import render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from app.coordinator import coordinator_bp
from app.auth.routes import coordinator_required
from app.models import db, User, Task, TaskLevel, Submission, Evaluation, Score, Notification
from app.coordinator.forms import EvaluationForm
from app.coordinator.code_analyzer import CodeAnalyzer
from sqlalchemy import desc
import os
import tempfile
import git
import shutil
from datetime import datetime
import requests
import json
import re

def analyze_github_repo(repo_url):
    """Analyze GitHub repository for automated scoring"""
    try:
        # Extract owner and repo from GitHub URL
        match = re.search(r'github.com/([^/]+)/([^/]+)', repo_url)
        if not match:
            return None
        
        owner, repo = match.groups()
        
        # GitHub API endpoint
        api_url = f'https://api.github.com/repos/{owner}/{repo}'
        headers = {'Accept': 'application/vnd.github.v3+json'}
        
        # Get repository info
        repo_info = requests.get(api_url, headers=headers).json()
        
        # Get commit history
        commits_url = f'{api_url}/commits'
        commits = requests.get(commits_url, headers=headers).json()
        
        # Get repository contents
        contents_url = f'{api_url}/contents'
        contents = requests.get(contents_url, headers=headers).json()
        
        # Analyze metrics
        metrics = {
            'Commit Count': len(commits),
            'Repository Size': repo_info.get('size', 0),
            'Has Documentation': any(file.get('name', '').lower() in ['readme.md', 'docs'] for file in contents if isinstance(file, dict)),
            'Last Updated': repo_info.get('updated_at', 'Unknown')
        }
        
        # Calculate suggested scores
        suggested_scores = {
            'functionality_score': min(40, 30 + (metrics['Commit Count'] // 5)),
            'code_quality_score': 15,  # Base score, needs manual review
            'performance_score': 15,   # Base score, needs manual review
            'documentation_score': 10 if metrics['Has Documentation'] else 5,
            'security_score': 8        # Base score, needs manual review
        }
        
        return {
            'metrics': metrics,
            'suggested_scores': suggested_scores
        }
        
    except Exception as e:
        current_app.logger.error(f'Error analyzing GitHub repo: {str(e)}')
        return None

def clone_and_analyze_repo(repo_url):
    """Clone repository and analyze code"""
    temp_dir = tempfile.mkdtemp()
    try:
        # Clone the repository
        git.Repo.clone_from(repo_url, temp_dir)
        
        # Initialize analyzer
        analyzer = CodeAnalyzer(temp_dir)
        
        # Define requirements for functionality analysis
        requirements = [
            {'name': 'Database Models', 'keywords': ['db.model', 'db.column'], 'points': 8},
            {'name': 'Route Handlers', 'keywords': ['@app.route', '@blueprint.route'], 'points': 8},
            {'name': 'Form Validation', 'keywords': ['form.validate', 'validators.'], 'points': 8},
            {'name': 'Authentication', 'keywords': ['login_required', 'current_user'], 'points': 8},
            {'name': 'Error Handling', 'keywords': ['try:', 'except', 'error'], 'points': 8}
        ]
        
        # Perform analysis
        results = analyzer.analyze_code(requirements)
        return results
        
    except Exception as e:
        current_app.logger.error(f'Error analyzing repository: {str(e)}')
        return None
    finally:
        # Clean up
        shutil.rmtree(temp_dir)

@coordinator_bp.route('/dashboard')
@login_required
@coordinator_required
def dashboard():
    pending_submissions = Submission.query.filter_by(status='submitted').count()
    total_students = User.query.filter_by(role='student').count()
    active_tasks = Task.query.filter_by(is_active=True).count()
    
    return render_template('coordinator/dashboard.html',
                         pending_submissions=pending_submissions,
                         total_students=total_students,
                         active_tasks=active_tasks)

# Task Level Management
@coordinator_bp.route('/levels', methods=['GET', 'POST'])
@login_required
@coordinator_required
def manage_levels():
    if request.method == 'POST':
        level_number = request.form.get('level_number', type=int)
        title = request.form.get('title')
        description = request.form.get('description')
        learning_objectives = request.form.get('learning_objectives')
        prerequisites = request.form.getlist('prerequisites[]')
        weight = request.form.get('weight', type=float, default=1.0)
        is_mandatory = request.form.get('is_mandatory') == 'true'
        
        level = TaskLevel(
            level_number=level_number,
            title=title,
            description=description,
            learning_objectives=learning_objectives,
            prerequisites=json.dumps(prerequisites) if prerequisites else None,
            weight=weight,
            is_mandatory=is_mandatory
        )
        
        db.session.add(level)
        db.session.commit()
        flash('Level created successfully', 'success')
        return redirect(url_for('coordinator.manage_levels'))
    
    levels = TaskLevel.query.order_by(TaskLevel.level_number).all()
    return render_template('coordinator/levels.html', levels=levels)

# Task Management
@coordinator_bp.route('/tasks', methods=['GET', 'POST'])
@login_required
@coordinator_required
def manage_tasks():
    if request.method == 'POST':
        level_id = request.form.get('level_id', type=int)
        title = request.form.get('title')
        description = request.form.get('description')
        task_type = request.form.get('task_type')
        notion_url = request.form.get('notion_url')
        github_template = request.form.get('github_template')
        deadline = datetime.strptime(request.form.get('deadline'), '%Y-%m-%dT%H:%M')
        
        # Custom evaluation criteria
        criteria = {
            'functionality': request.form.get('functionality_weight', type=int, default=40),
            'code_quality': request.form.get('code_quality_weight', type=int, default=20),
            'performance': request.form.get('performance_weight', type=int, default=20),
            'documentation': request.form.get('documentation_weight', type=int, default=10),
            'security': request.form.get('security_weight', type=int, default=10)
        }
        
        task = Task(
            level_id=level_id,
            title=title,
            description=description,
            task_type=task_type,
            notion_url=notion_url,
            github_template_url=github_template,
            deadline=deadline,
            created_by=current_user.id,
            evaluation_criteria=json.dumps(criteria)
        )
        
        db.session.add(task)
        db.session.commit()
        
        # Notify all eligible students
        level = TaskLevel.query.get(level_id)
        eligible_students = User.query.filter_by(
            role='student',
            is_active=True,
            current_level=level.level_number
        ).all()
        
        for student in eligible_students:
            notification = Notification(
                user_id=student.id,
                title=f'New Task: {title}',
                message=f'A new task has been assigned for Level {level.level_number}',
                type='task_assigned'
            )
            db.session.add(notification)
        
        db.session.commit()
        flash('Task created and students notified', 'success')
        return redirect(url_for('coordinator.manage_tasks'))
    
    levels = TaskLevel.query.order_by(TaskLevel.level_number).all()
    tasks = Task.query.order_by(desc(Task.created_at)).all()
    return render_template('coordinator/tasks.html', levels=levels, tasks=tasks)

# Submission Management
@coordinator_bp.route('/submissions')
@login_required
@coordinator_required
def view_submissions():
    submissions = Submission.query\
        .join(Task)\
        .join(User)\
        .order_by(desc(Submission.submitted_at))\
        .all()
    return render_template('coordinator/submissions.html', submissions=submissions)

@coordinator_bp.route('/submission/<int:submission_id>/evaluate', methods=['GET', 'POST'])
@login_required
@coordinator_required
def evaluate_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    form = EvaluationForm()
    
    # Get or create evaluation
    evaluation = Evaluation.query.filter_by(submission_id=submission_id).first()
    if not evaluation:
        evaluation = Evaluation(
            submission_id=submission_id,
            task_id=submission.task_id,
            evaluator_id=current_user.id
        )
        db.session.add(evaluation)
    
    # Handle form submission
    if form.validate_on_submit():
        # Update manual scores
        evaluation.functionality_score = form.functionality_score.data
        evaluation.code_quality_score = form.code_quality_score.data
        evaluation.performance_score = form.performance_score.data
        evaluation.documentation_score = form.documentation_score.data
        evaluation.security_score = form.security_score.data
        evaluation.feedback = form.feedback.data
        
        # Perform automated analysis if not done yet
        if not evaluation.automated_results:
            try:
                # Clone repository for analysis
                with tempfile.TemporaryDirectory() as temp_dir:
                    repo_path = os.path.join(temp_dir, 'repo')
                    git.Repo.clone_from(submission.submission_url, repo_path)
                    
                    # Run automated analysis
                    analyzer = CodeAnalyzer(repo_path)
                    results = analyzer.analyze()
                    
                    # Store automated results
                    evaluation.automated_results = json.dumps(results)
                    evaluation.automated_score = sum(results['scores'].values()) / len(results['scores'])
                    evaluation.automated_feedback = json.dumps({
                        'code_smells': results['details']['code_smells'],
                        'security_issues': results['details']['security_issues'],
                        'performance_issues': results['details']['performance_issues'],
                        'documentation_issues': results['details']['documentation_issues'],
                        'missing_features': results['details']['missing_features']
                    })
            except Exception as e:
                flash(f'Error during automated analysis: {str(e)}', 'error')
                evaluation.automated_score = 0
                evaluation.automated_feedback = json.dumps({'error': str(e)})
        
        # Calculate total score
        evaluation.calculate_total_score()
        
        # Update submission status
        submission.status = 'evaluated'
        
        # Update student's monthly score
        now = datetime.utcnow()
        student = submission.user
        score = Score.query.filter_by(
            user_id=student.id,
            month=now.month,
            year=now.year
        ).first()
        
        if not score:
            score = Score(
                user_id=student.id,
                month=now.month,
                year=now.year
            )
            db.session.add(score)
        
        # Calculate new total score for the month
        student_submissions = Submission.query.filter_by(
            user_id=student.id,
            status='evaluated'
        ).all()
        score.calculate_total_score(student_submissions)
        
        # Notify student
        notification = Notification(
            user_id=student.id,
            title='Task Evaluated',
            message=f'Your submission for {submission.task.title} has been evaluated. Check your score and feedback.',
            type='evaluation_complete'
        )
        db.session.add(notification)
        
        # Save all changes
        db.session.commit()
        flash('Evaluation submitted successfully!', 'success')
        return redirect(url_for('coordinator.view_submissions'))
    
    # Pre-fill form with existing values
    elif request.method == 'GET' and evaluation.id:
        form.functionality_score.data = evaluation.functionality_score
        form.code_quality_score.data = evaluation.code_quality_score
        form.performance_score.data = evaluation.performance_score
        form.documentation_score.data = evaluation.documentation_score
        form.security_score.data = evaluation.security_score
        form.feedback.data = evaluation.feedback
    
    # Get automated analysis results
    analysis_results = None
    if evaluation.automated_results:
        analysis_results = {
            'scores': json.loads(evaluation.automated_results)['scores'],
            'details': json.loads(evaluation.automated_feedback)
        }
    
    return render_template('coordinator/evaluate.html', 
                         form=form, 
                         submission=submission,
                         analysis_results=analysis_results)

@coordinator_bp.route('/api/analyze-submission/<int:submission_id>', methods=['GET'])
@login_required
@coordinator_required
def analyze_submission(submission_id):
    """API endpoint to run automated analysis on a submission."""
    try:
        submission = Submission.query.get_or_404(submission_id)
        
        # Get or create evaluation
        evaluation = Evaluation.query.filter_by(submission_id=submission_id).first()
        if not evaluation:
            evaluation = Evaluation(
                submission_id=submission_id,
                task_id=submission.task_id,
                evaluator_id=current_user.id
            )
            db.session.add(evaluation)
        
        # Create temporary directory for cloning
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = os.path.join(temp_dir, 'repo')
            
            # Extract repository owner and name from URL
            repo_url = submission.submission_url
            if not repo_url:
                return jsonify({'success': False, 'error': 'No repository URL provided'})
            
            # Clone repository
            try:
                git.Repo.clone_from(repo_url, repo_path)
            except git.exc.GitCommandError as e:
                return jsonify({'success': False, 'error': f'Failed to clone repository: {str(e)}'})
            
            # Run analysis
            analyzer = CodeAnalyzer(repo_path)
            results = analyzer.analyze()
            
            # Store results
            evaluation.automated_results = json.dumps(results)
            
            # Calculate automated score (average of all scores)
            scores = results['scores']
            evaluation.automated_score = sum(scores.values()) / len(scores)
            
            # Store automated feedback
            evaluation.automated_feedback = json.dumps({
                'code_smells': results['details']['code_smells'],
                'security_issues': results['details']['security_issues'],
                'performance_issues': results['details']['performance_issues'],
                'documentation_issues': results['details']['documentation_issues'],
                'missing_features': results['details']['missing_features']
            })
            
            # Calculate total score if manual scores exist
            if all([
                evaluation.functionality_score,
                evaluation.code_quality_score,
                evaluation.performance_score,
                evaluation.documentation_score,
                evaluation.security_score
            ]):
                evaluation.calculate_total_score()
            
            db.session.commit()
            
            return jsonify({'success': True})
            
    except Exception as e:
        current_app.logger.error(f'Error in automated analysis: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})

# Non-submission Tracking
@coordinator_bp.route('/non-submissions')
@login_required
@coordinator_required
def track_non_submissions():
    selected_task_id = request.args.get('task_id', type=int)
    active_tasks = Task.query.filter_by(is_active=True).all()
    students = User.query.filter_by(role='student', is_active=True).all()
    
    non_submissions = {}
    if selected_task_id:
        # If a specific task is selected
        task = Task.query.get(selected_task_id)
        if task:
            submitted_students = db.session.query(User.id).join(Submission)\
                .filter(Submission.task_id == task.id).all()
            submitted_ids = [s[0] for s in submitted_students]
            missing_students = [s for s in students if s.id not in submitted_ids]
            for student in missing_students:
                non_submissions[student] = [task]
    else:
        # Show all missing submissions for each student
        for student in students:
            missing_tasks = []
            for task in active_tasks:
                submission = Submission.query.filter_by(
                    user_id=student.id,
                    task_id=task.id
                ).first()
                if not submission:
                    missing_tasks.append(task)
            if missing_tasks:
                non_submissions[student] = missing_tasks
    
    return render_template('coordinator/non_submissions.html',
                         tasks=active_tasks,
                         non_submissions=non_submissions,
                         selected_task_id=selected_task_id)

@coordinator_bp.route('/send-reminder', methods=['POST'])
@login_required
@coordinator_required
def send_reminder():
    try:
        data = request.get_json()
        student_email = data.get('email')
        student_name = data.get('name')
        task_id = data.get('task_id')
        
        if not all([student_email, student_name, task_id]):
            return jsonify({'success': False, 'error': 'Missing required data'}), 400
            
        task = Task.query.get_or_404(task_id)
        student = User.query.filter_by(email=student_email).first()
        
        if not student:
            return jsonify({'success': False, 'error': 'Student not found'}), 404
            
        # Create notification for student
        notification = Notification(
            user_id=student.id,
            title=f'Task Submission Reminder: {task.title}',
            message=f'This is a reminder that you have not yet submitted your work for the task "{task.title}". The deadline is {task.deadline.strftime("%Y-%m-%d %H:%M")}.',
            type='reminder'
        )
        db.session.add(notification)
        
        # Send email notification
        try:
            msg = Message(
                f'Task Submission Reminder: {task.title}',
                recipients=[student_email]
            )
            msg.body = f'''
Hello {student_name},

This is a reminder that you have not yet submitted your work for the following task:

Task: {task.title}
Deadline: {task.deadline.strftime('%Y-%m-%d %H:%M')}

Please submit your work as soon as possible. If you are facing any difficulties, 
please reach out to your coordinator.

Best regards,
TIC TaskApp Team
            '''
            mail.send(msg)
        except Exception as e:
            current_app.logger.error(f'Failed to send reminder email: {str(e)}')
            # Continue even if email fails, at least notification is created
        
        db.session.commit()
        return jsonify({'success': True}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error sending reminder: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500
