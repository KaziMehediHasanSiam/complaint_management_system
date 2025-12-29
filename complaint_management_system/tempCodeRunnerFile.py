from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config.from_object('config.Config')

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False, default='user')  # admin, staff, user
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    responses = db.relationship('Response', backref='complaint', lazy=True)

class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaint.id'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
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
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('login.html', register=True)
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return render_template('login.html', register=True)
        
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('login.html', register=True)

@app.route('/dashboard')
@login_required
def dashboard():
    # Statistics for dashboard
    total_complaints = Complaint.query.count()
    user_complaints = Complaint.query.filter_by(user_id=current_user.id).count()
    open_complaints = Complaint.query.filter_by(status='Open').count()
    resolved_complaints = Complaint.query.filter_by(status='Resolved').count()
    
    # Recent complaints
    if current_user.role in ['admin', 'staff']:
        recent_complaints = Complaint.query.order_by(Complaint.created_at.desc()).limit(5).all()
    else:
        recent_complaints = Complaint.query.filter_by(user_id=current_user.id).order_by(Complaint.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html',
                         total_complaints=total_complaints,
                         user_complaints=user_complaints,
                         open_complaints=open_complaints,
                         resolved_complaints=resolved_complaints,
                         recent_complaints=recent_complaints)

@app.route('/submit_complaint', methods=['GET', 'POST'])
@login_required
def submit_complaint():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        priority = request.form.get('priority')
        
        complaint = Complaint(
            title=title,
            description=description,
            category=category,
            priority=priority,
            user_id=current_user.id
        )
        
        db.session.add(complaint)
        db.session.commit()
        
        flash('Complaint submitted successfully!', 'success')
        return redirect(url_for('view_complaints'))
    
    return render_template('submit_complaint.html')

@app.route('/view_complaints')
@login_required
def view_complaints():
    if current_user.role in ['admin', 'staff']:
        complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    else:
        complaints = Complaint.query.filter_by(user_id=current_user.id).order_by(Complaint.created_at.desc()).all()
    
    return render_template('view_complaints.html', complaints=complaints)

@app.route('/complaint/<int:complaint_id>')
@login_required
def complaint_detail(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    
    # Check if user has permission to view this complaint
    if current_user.role not in ['admin', 'staff'] and complaint.user_id != current_user.id:
        flash('You do not have permission to view this complaint', 'danger')
        return redirect(url_for('view_complaints'))
    
    return render_template('complaint_detail.html', complaint=complaint)

@app.route('/respond/<int:complaint_id>', methods=['GET', 'POST'])
@login_required
def respond_complaint(complaint_id):
    if current_user.role not in ['admin', 'staff']:
        flash('You do not have permission to respond to complaints', 'danger')
        return redirect(url_for('view_complaints'))
    
    complaint = Complaint.query.get_or_404(complaint_id)
    
    if request.method == 'POST':
        message = request.form.get('message')
        status = request.form.get('status')
        
        response = Response(
            complaint_id=complaint_id,
            staff_id=current_user.id,
            message=message
        )
        
        complaint.status = status
        complaint.updated_at = datetime.utcnow()
        
        db.session.add(response)
        db.session.commit()
        
        flash('Response submitted successfully!', 'success')
        return redirect(url_for('complaint_detail', complaint_id=complaint_id))
    
    return render_template('respond.html', complaint=complaint)

@app.route('/report')
@login_required
def report():
    if current_user.role not in ['admin', 'staff']:
        flash('You do not have permission to view reports', 'danger')
        return redirect(url_for('dashboard'))
    
    # Complaint statistics by category
    category_stats = db.session.query(
        Complaint.category,
        db.func.count(Complaint.id)
    ).group_by(Complaint.category).all()
    
    # Complaint statistics by status
    status_stats = db.session.query(
        Complaint.status,
        db.func.count(Complaint.id)
    ).group_by(Complaint.status).all()
    
    # Complaint statistics by priority
    priority_stats = db.session.query(
        Complaint.priority,
        db.func.count(Complaint.id)
    ).group_by(Complaint.priority).all()
    
    return render_template('report.html',
                         category_stats=category_stats,
                         status_stats=status_stats,
                         priority_stats=priority_stats)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully!', 'success')
    return redirect(url_for('login'))

# API Routes
@app.route('/api/complaints')
@login_required
def api_complaints():
    if current_user.role in ['admin', 'staff']:
        complaints = Complaint.query.all()
    else:
        complaints = Complaint.query.filter_by(user_id=current_user.id).all()
    
    complaints_data = []
    for complaint in complaints:
        complaints_data.append({
            'id': complaint.id,
            'title': complaint.title,
            'category': complaint.category,
            'priority': complaint.priority,
            'status': complaint.status,
            'created_at': complaint.created_at.isoformat(),
            'author': complaint.author.username
        })
    
    return jsonify(complaints_data)

# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@example.com', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
    
    app.run(debug=True)