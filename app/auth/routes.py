from functools import wraps
from flask import redirect, url_for, flash, session, current_app, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import google
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError, InvalidClientIdError
from app.auth import auth_bp
from app.models import User, db
from datetime import datetime
import json

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You need to be an admin to access this page.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def coordinator_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'coordinator':
            flash('You need to be a coordinator to access this page.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login')
def login():
    if not google.authorized:
        print("Not authorized, redirecting to Google login")
        return redirect(url_for('google.login'))
    return redirect(url_for('auth.google_authorized'))

def redirect_by_role(user):
    print(f"Redirecting user {user.email} with role {user.role}")
    if user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif user.role == 'coordinator':
        return redirect(url_for('coordinator.dashboard'))
    elif user.role == 'student':
        return redirect(url_for('student.dashboard'))
    return redirect(url_for('main.index'))

@auth_bp.route('/google/authorized')
def google_authorized():
    try:
        print("Starting Google authorization...")
        if not google.authorized:
            print("Not authorized by Google")
            flash('Authentication failed. Please try again.', 'error')
            return redirect(url_for('main.index'))

        try:
            print("Getting user info from Google...")
            resp = google.get('/oauth2/v2/userinfo')
            print(f"Response status: {resp.status_code}")
            if not resp.ok:
                print(f"Failed to get user info. Status: {resp.status_code}")
                flash('Failed to get user info from Google.', 'error')
                return redirect(url_for('main.index'))
            google_info = resp.json()
            print(f"Google Info received: {json.dumps(google_info, indent=2)}")
        except TokenExpiredError:
            print("Token expired")
            flash('Session expired. Please login again.', 'error')
            return redirect(url_for('auth.login'))
        except Exception as e:
            print(f"Error getting Google info: {str(e)}")
            flash('Failed to get user info from Google.', 'error')
            return redirect(url_for('main.index'))

        email = google_info.get('email')
        if not email:
            print("No email in Google response")
            flash('Failed to get email from Google.', 'error')
            return redirect(url_for('main.index'))

        # Verify domain
        domain = email.split('@')[1]
        print(f"User domain: {domain}")
        if domain not in current_app.config['ALLOWED_DOMAINS']:
            print(f"Domain {domain} not in allowed domains")
            flash(f'Access restricted to {current_app.config["ALLOWED_DOMAINS"]} domain only.', 'error')
            return redirect(url_for('main.index'))

        # Check if user exists
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"Creating new user for {email}")
            # Determine role based on email
            if email == current_app.config['ADMIN_EMAIL']:
                role = 'admin'
            elif email == current_app.config['COORDINATOR_EMAIL']:
                role = 'coordinator'
            else:
                role = 'student'
            
            print(f"Assigned role: {role}")
            user = User(
                email=email,
                google_id=google_info['id'],
                name=google_info.get('name', email.split('@')[0]),
                role=role,
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            try:
                print("Adding new user to database...")
                db.session.add(user)
                db.session.commit()
                print("User added successfully")
            except Exception as e:
                print(f"Database error creating user: {str(e)}")
                db.session.rollback()
                flash('Error creating user account.', 'error')
                return redirect(url_for('main.index'))
        else:
            print(f"Existing user found: {user.email} with role {user.role}")
            user.last_login = datetime.utcnow()
            try:
                db.session.commit()
                print("Updated last login time")
            except Exception as e:
                print(f"Error updating last login: {str(e)}")
                db.session.rollback()

        # Login user
        print(f"Logging in user {user.email}")
        login_user(user)
        flash(f'Welcome, {user.name}!', 'success')
        
        # Redirect based on role
        print(f"Redirecting user to dashboard based on role: {user.role}")
        return redirect_by_role(user)

    except Exception as e:
        print(f"Error in google_authorized: {str(e)}")
        flash('An error occurred during login.', 'error')
        return redirect(url_for('main.index'))

@auth_bp.route('/debug/session')
def debug_session():
    output = {
        'is_authenticated': current_user.is_authenticated,
        'user_info': {
            'id': current_user.id,
            'email': current_user.email,
            'role': current_user.role,
            'name': current_user.name
        } if current_user.is_authenticated else None,
        'session': dict(session)
    }
    return jsonify(output)

@auth_bp.route('/debug/users')
def debug_users():
    users = User.query.all()
    output = [{
        'id': user.id,
        'email': user.email,
        'role': user.role,
        'name': user.name,
        'last_login': str(user.last_login)
    } for user in users]
    return jsonify(output)

@auth_bp.route('/logout')
@login_required
def logout():
    print(f"Logging out user: {current_user.email if current_user.is_authenticated else 'No user'}")
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))
