import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urljoin

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config.from_object('config.Config')

db = SQLAlchemy(app)
csrf = CSRFProtect(app)  # protects every POST form with a hidden csrf_token
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
USERNAME_RE = re.compile(r'^(?=.*[A-Za-z])[A-Za-z0-9_.]{3,20}$')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
COMMON_PASSWORDS = {'password', 'password1', '12345678', 'qwerty123', 'admin123', 'iloveyou'}

CATEGORIES = {
    'Technical': 'Technical Issue',
    'Billing': 'Billing Problem',
    'Service': 'Service Quality',
    'Facility': 'Facility Issue',
    'Staff': 'Staff Behavior',
    'Other': 'Other',
}
PRIORITIES = ['Low', 'Medium', 'High', 'Critical']
STATUSES = ['Open', 'In Progress', 'Resolved', 'Closed']
STAFF_ROLES = ('admin', 'staff')

BD_TZ = timezone(timedelta(hours=6))  # Bangladesh Standard Time (no daylight saving)


def utcnow():
    """Naive UTC time. Replacement for the deprecated datetime.utcnow()."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Database models
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(500))
    role = db.Column(db.String(20), nullable=False, default='user')  # admin, staff, user
    created_at = db.Column(db.DateTime, default=utcnow)
    complaints = db.relationship('Complaint', backref='author', lazy=True)
    responses = db.relationship('Response', backref='staff', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.String(20), default='Medium')  # Low, Medium, High, Critical
    status = db.Column(db.String(20), default='Open')  # Open, In Progress, Resolved, Closed
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    responses = db.relationship('Response', backref='complaint', lazy=True,
                                order_by='Response.created_at')


class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaint.id'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def is_staff():
    return current_user.is_authenticated and current_user.role in STAFF_ROLES


def is_safe_url(target):
    """Allow only redirects that stay on this site (prevents open redirect)."""
    if not target or '\\' in target:
        return False
    host = urlparse(request.host_url)
    test = urlparse(urljoin(request.host_url, target))
    return test.scheme in ('http', 'https') and host.netloc == test.netloc


def username_taken(name):
    return User.query.filter(db.func.lower(User.username) == name.lower()).first() is not None


def validate_registration(username, email, password, confirm):
    errors = []

    if not USERNAME_RE.match(username):
        errors.append('Username must be 3-20 characters (letters, numbers, _ or .) and include at least one letter.')
    elif username_taken(username):
        errors.append('This username is already taken. Please choose another one.')

    if not EMAIL_RE.match(email):
        errors.append('Please enter a valid email address.')
    elif User.query.filter(db.func.lower(User.email) == email.lower()).first():
        errors.append('An account with this email already exists.')

    if len(password) < 8:
        errors.append('Password must be at least 8 characters.')
    if not re.search(r'[A-Z]', password):
        errors.append('Password needs an uppercase letter.')
    if not re.search(r'[a-z]', password):
        errors.append('Password needs a lowercase letter.')
    if not re.search(r'[0-9]', password):
        errors.append('Password needs a number.')
    if not re.search(r'[^A-Za-z0-9]', password):
        errors.append('Password needs a symbol (for example ! @ # $).')
    if username and username.lower() in password.lower():
        errors.append('Password must not contain your username.')
    if password.lower() in COMMON_PASSWORDS:
        errors.append('This password is too common.')
    if password != confirm:
        errors.append('Passwords do not match.')

    return errors


def validate_complaint(title, description, category, priority):
    errors = []
    if not 3 <= len(title) <= 200:
        errors.append('Title must be between 3 and 200 characters.')
    if not 10 <= len(description) <= 5000:
        errors.append('Description must be between 10 and 5000 characters.')
    if category not in CATEGORIES:
        errors.append('Please choose a valid category.')
    if priority not in PRIORITIES:
        errors.append('Please choose a valid priority.')
    return errors


def count_by(column):
    rows = (db.session.query(column, db.func.count(Complaint.id))
            .group_by(column)
            .order_by(db.func.count(Complaint.id).desc())
            .all())
    return [(label, count) for label, count in rows]


@app.template_filter('bdtime')
def bdtime(value, fmt='%d %b %Y, %I:%M %p'):
    """Show a stored UTC time in Bangladesh time."""
    if not value:
        return ''
    return value.replace(tzinfo=timezone.utc).astimezone(BD_TZ).strftime(fmt)


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        user = User.query.filter(db.func.lower(User.username) == username.lower()).first()

        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page if is_safe_url(next_page) else url_for('dashboard'))
        flash('Invalid username or password', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip()
        password = request.form.get('password') or ''
        confirm = request.form.get('confirm') or ''

        errors = validate_registration(username, email, password, confirm)
        if errors:
            for message in errors:
                flash(message, 'danger')
            return render_template('login.html', register=True, form=request.form)

        user = User(username=username, email=email, role='user')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('login.html', register=True)


@app.route('/api/check_username')
def check_username():
    name = (request.args.get('u') or '').strip()
    if not USERNAME_RE.match(name):
        return jsonify(valid=False, available=False,
                       message='3-20 characters, letters/numbers/_/. only, at least one letter')
    if username_taken(name):
        return jsonify(valid=True, available=False, message='Username is already taken')
    return jsonify(valid=True, available=True, message='Username is available')


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully!', 'success')
    return redirect(url_for('login'))


# ---------------------------------------------------------------------------
# Complaint routes
# ---------------------------------------------------------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    # Staff see every complaint, normal users only see their own numbers.
    scope = Complaint.query if is_staff() else Complaint.query.filter_by(user_id=current_user.id)

    return render_template('dashboard.html',
                           total_complaints=scope.count(),
                           open_complaints=scope.filter_by(status='Open').count(),
                           in_progress_complaints=scope.filter_by(status='In Progress').count(),
                           resolved_complaints=scope.filter_by(status='Resolved').count(),
                           recent_complaints=scope.order_by(Complaint.created_at.desc()).limit(5).all())


@app.route('/submit_complaint', methods=['GET', 'POST'])
@login_required
def submit_complaint():
    form = None
    if request.method == 'POST':
        form = request.form
        title = (form.get('title') or '').strip()
        description = (form.get('description') or '').strip()
        category = form.get('category') or ''
        priority = form.get('priority') or ''

        errors = validate_complaint(title, description, category, priority)
        if not errors:
            complaint = Complaint(title=title, description=description,
                                  category=category, priority=priority,
                                  user_id=current_user.id)
            db.session.add(complaint)
            db.session.commit()
            flash('Complaint submitted successfully!', 'success')
            return redirect(url_for('view_complaints'))

        for message in errors:
            flash(message, 'danger')

    return render_template('submit_complaint.html', form=form,
                           categories=CATEGORIES, priorities=PRIORITIES)


@app.route('/view_complaints')
@login_required
def view_complaints():
    query = Complaint.query if is_staff() else Complaint.query.filter_by(user_id=current_user.id)
    complaints = query.order_by(Complaint.created_at.desc()).all()
    return render_template('view_complaints.html', complaints=complaints)


@app.route('/complaint/<int:complaint_id>')
@login_required
def complaint_detail(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)

    if not is_staff() and complaint.user_id != current_user.id:
        flash('You do not have permission to view this complaint', 'danger')
        return redirect(url_for('view_complaints'))

    return render_template('complaint_detail.html', complaint=complaint)


@app.route('/respond/<int:complaint_id>', methods=['GET', 'POST'])
@login_required
def respond_complaint(complaint_id):
    if not is_staff():
        flash('You do not have permission to respond to complaints', 'danger')
        return redirect(url_for('view_complaints'))

    complaint = Complaint.query.get_or_404(complaint_id)
    form = None

    if request.method == 'POST':
        form = request.form
        message = (form.get('message') or '').strip()
        status = form.get('status') or ''

        errors = []
        if not 1 <= len(message) <= 5000:
            errors.append('Response message must be between 1 and 5000 characters.')
        if status not in STATUSES:
            errors.append('Please choose a valid status.')

        if not errors:
            db.session.add(Response(complaint_id=complaint.id, staff_id=current_user.id, message=message))
            complaint.status = status
            complaint.updated_at = utcnow()
            db.session.commit()
            flash('Response submitted successfully!', 'success')
            return redirect(url_for('complaint_detail', complaint_id=complaint.id))

        for text in errors:
            flash(text, 'danger')

    return render_template('respond.html', complaint=complaint, form=form, statuses=STATUSES)


@app.route('/report')
@login_required
def report():
    if not is_staff():
        flash('You do not have permission to view reports', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('report.html',
                           total=Complaint.query.count(),
                           category_stats=count_by(Complaint.category),
                           status_stats=count_by(Complaint.status),
                           priority_stats=count_by(Complaint.priority))


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.route('/api/complaints')
@login_required
def api_complaints():
    query = Complaint.query if is_staff() else Complaint.query.filter_by(user_id=current_user.id)

    return jsonify([{
        'id': c.id,
        'title': c.title,
        'category': c.category,
        'priority': c.priority,
        'status': c.status,
        'created_at': c.created_at.isoformat(),
        'author': c.author.username,
    } for c in query.all()])


# ---------------------------------------------------------------------------
# Error handlers and template context
# ---------------------------------------------------------------------------
@app.errorhandler(CSRFError)
def csrf_error(error):
    flash('Your session expired or the form was invalid. Please try again.', 'danger')
    return redirect(url_for('dashboard'))


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


@app.context_processor
def inject_now():
    return {'now': utcnow()}


# ---------------------------------------------------------------------------
# Start-up
# ---------------------------------------------------------------------------
def create_default_admin():
    """Create the first admin. The password comes from ADMIN_PASSWORD or is generated once."""
    if User.query.filter_by(username='admin').first():
        return

    password = os.environ.get('ADMIN_PASSWORD')
    generated = not password
    if generated:
        password = secrets.token_urlsafe(10)

    admin = User(username='admin', email='admin@example.com', role='admin')
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()

    if generated:
        print(f'\n[setup] Admin account created -> username: admin | password: {password}\n')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_default_admin()

    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
