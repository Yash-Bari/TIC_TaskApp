from flask import render_template
from flask_login import login_required
from app.coordinator import coordinator_bp
from app.auth.routes import coordinator_required

@coordinator_bp.route('/dashboard')
@login_required
@coordinator_required
def dashboard():
    return render_template('coordinator/dashboard.html')
