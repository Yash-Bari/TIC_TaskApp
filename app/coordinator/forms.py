from flask_wtf import FlaskForm
from wtforms import FloatField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class EvaluationForm(FlaskForm):
    functionality_score = FloatField('Functionality (40%)', 
        validators=[DataRequired(), NumberRange(min=0, max=40)],
        description='How well does the code fulfill the requirements?')
    
    code_quality_score = FloatField('Code Quality (20%)', 
        validators=[DataRequired(), NumberRange(min=0, max=20)],
        description='Code organization, readability, and best practices')
    
    performance_score = FloatField('Performance (20%)', 
        validators=[DataRequired(), NumberRange(min=0, max=20)],
        description='Code efficiency and resource utilization')
    
    documentation_score = FloatField('Documentation (10%)', 
        validators=[DataRequired(), NumberRange(min=0, max=10)],
        description='Code comments, README, and documentation quality')
    
    security_score = FloatField('Security (10%)', 
        validators=[DataRequired(), NumberRange(min=0, max=10)],
        description='Code security practices and vulnerability prevention')
    
    feedback = TextAreaField('Feedback',
        validators=[DataRequired()],
        description='Provide detailed feedback for the student')
    
    submit = SubmitField('Submit Evaluation')
