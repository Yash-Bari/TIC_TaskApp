from flask import render_template
from flask_login import login_required
from app.admin import admin_bp
from app.auth.routes import admin_required

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')
