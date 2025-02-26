from datetime import datetime
from flask_login import UserMixin
from app import db, login_manager
import json

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class TaskLevel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    level_number = db.Column(db.Integer, nullable=False, unique=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    learning_objectives = db.Column(db.Text, nullable=False)
    prerequisites = db.Column(db.Text)  # JSON list of required level numbers
    weight = db.Column(db.Float, default=1.0)
    is_mandatory = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    tasks = db.relationship('Task', backref='level', lazy=True)
    
    def get_prerequisites(self):
        if self.prerequisites:
            return json.loads(self.prerequisites)
        return []

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    google_id = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='student')  # student, coordinator, admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    current_level = db.Column(db.Integer, default=1)  # Track student's current level
    
    # Relationships
    submissions = db.relationship('Submission', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    scores = db.relationship('Score', backref='user', lazy=True)
    tasks_created = db.relationship('Task', backref='creator', lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    level_id = db.Column(db.Integer, db.ForeignKey('task_level.id'), nullable=False)
    task_type = db.Column(db.String(50), nullable=False)  # project, exercise, quiz
    notion_url = db.Column(db.String(500))
    github_template_url = db.Column(db.String(500))  # Optional starter template
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.DateTime, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    max_score = db.Column(db.Float, default=100.0)
    evaluation_criteria = db.Column(db.Text)  # JSON object with specific criteria
    
    # Relationships
    submissions = db.relationship('Submission', backref='task', lazy=True)
    evaluations = db.relationship('Evaluation', backref='task', lazy=True)
    
    def get_evaluation_criteria(self):
        if self.evaluation_criteria:
            return json.loads(self.evaluation_criteria)
        return {
            'functionality': 40,
            'code_quality': 20,
            'performance': 20,
            'documentation': 10,
            'security': 10
        }

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    submission_url = db.Column(db.String(500), nullable=False)  # GitHub repository URL
    live_demo_url = db.Column(db.String(500))  # Optional live demo URL
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='submitted')  # submitted, evaluated
    
    # Relationship
    evaluation = db.relationship('Evaluation', backref='submission', lazy=True, uselist=False)

class Evaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    evaluator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    evaluated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Manual evaluation scores (40% of total)
    functionality_score = db.Column(db.Float)  # Out of 40
    code_quality_score = db.Column(db.Float)   # Out of 20
    performance_score = db.Column(db.Float)    # Out of 20
    documentation_score = db.Column(db.Float)  # Out of 10
    security_score = db.Column(db.Float)       # Out of 10
    
    # Automated evaluation (60% of total)
    automated_results = db.Column(db.Text)  # JSON with detailed analysis
    automated_score = db.Column(db.Float)   # Out of 100
    automated_feedback = db.Column(db.Text)
    
    total_score = db.Column(db.Float)
    feedback = db.Column(db.Text)
    
    evaluator = db.relationship('User', backref='evaluations_given', foreign_keys=[evaluator_id])

    def calculate_total_score(self):
        """Calculate total score based on manual and automated evaluations."""
        # Manual evaluation (40% of total)
        if all([
            self.functionality_score,
            self.code_quality_score,
            self.performance_score,
            self.documentation_score,
            self.security_score
        ]):
            manual_score = (
                self.functionality_score * 0.4 +  # 40% weight for functionality
                self.code_quality_score * 0.2 +   # 20% weight for code quality
                self.performance_score * 0.2 +    # 20% weight for performance
                self.documentation_score * 0.1 +  # 10% weight for documentation
                self.security_score * 0.1         # 10% weight for security
            )
        else:
            manual_score = 0
        
        # Automated evaluation (60% of total)
        automated_score = self.automated_score if self.automated_score is not None else 0
        
        # Calculate total (manual: 40%, automated: 60%)
        if manual_score > 0 or automated_score > 0:
            self.total_score = (manual_score * 0.4) + (automated_score * 0.6)
        else:
            self.total_score = None
            
        return self.total_score

    def get_automated_results(self):
        """Get parsed automated analysis results."""
        if self.automated_results:
            return json.loads(self.automated_results)
        return None

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    total_score = db.Column(db.Float, default=0)
    tasks_completed = db.Column(db.Integer, default=0)
    level_scores = db.Column(db.Text)  # JSON string storing scores for each level
    rank = db.Column(db.Integer)
    is_published = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'month', 'year'),)
    
    def get_level_scores(self):
        if self.level_scores:
            return json.loads(self.level_scores)
        return {}
    
    def set_level_scores(self, scores_dict):
        self.level_scores = json.dumps(scores_dict)
    
    def calculate_total_score(self, submissions):
        """Calculate total score based on evaluated submissions."""
        total_score = 0
        tasks_completed = 0
        level_scores = {}
        level_weights = {}

        # Get level weights from TaskLevel
        levels = TaskLevel.query.all()
        for level in levels:
            level_weights[level.level_number] = level.weight

        # Group scores by level
        for submission in submissions:
            if submission.evaluation and submission.status == 'evaluated':
                level_num = submission.task.level.level_number
                if level_num not in level_scores:
                    level_scores[level_num] = []
                
                # Only include submissions that have all required scores
                eval_scores = [
                    submission.evaluation.functionality_score,
                    submission.evaluation.code_quality_score,
                    submission.evaluation.performance_score,
                    submission.evaluation.documentation_score,
                    submission.evaluation.security_score
                ]
                
                if all(score is not None for score in eval_scores):
                    total = sum(eval_scores)
                    level_scores[level_num].append(total)

        # Check if mandatory level (Level 1) is completed
        if 1 not in level_scores or not level_scores[1]:
            self.total_score = 0
            self.tasks_completed = 0
            self.set_level_scores({})
            return 0

        # Calculate average score for each level and apply weights
        final_level_scores = {}
        for level_num, scores in level_scores.items():
            if scores:  # Only calculate if there are valid scores
                avg_score = sum(scores) / len(scores)
                weighted_score = avg_score * level_weights.get(level_num, 1.0)
                final_level_scores[level_num] = weighted_score
                total_score += weighted_score
                tasks_completed += len(scores)

        # Apply bonus for completing more levels
        num_levels_completed = len(final_level_scores)
        completion_bonus = num_levels_completed * 0.1  # 10% bonus per level completed
        total_score = total_score * (1 + completion_bonus)

        # Update score object
        self.total_score = round(total_score, 2)
        self.tasks_completed = tasks_completed
        self.set_level_scores(final_level_scores)
        self.updated_at = datetime.utcnow()

        return total_score

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50))  # task_assigned, deadline_reminder, evaluation_complete
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
