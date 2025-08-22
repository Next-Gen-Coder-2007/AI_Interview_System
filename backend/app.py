from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import base64
from sqlalchemy import func
import io
from PIL import Image
from datetime import datetime, timedelta
import json

def compress_and_convert_to_base64(image):
    img = Image.open(image)
    img.thumbnail((200, 200))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    img_base64 = base64.b64encode(img_byte_arr).decode('utf-8')
    return img_base64

app = Flask(__name__, template_folder="../frontend")
app.config['SECRET_KEY'] = '123456789'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    profile_picture = db.Column(db.Text, nullable=True)

class Interview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100))
    domain = db.Column(db.String(100))
    status = db.Column(db.String(100))
    description = db.Column(db.Text)
    duration = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='interviews')
    attempts = db.relationship('Attempt', backref='interview', lazy=True)

class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    attempt_number = db.Column(db.Integer, nullable=False, default=1)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow)
    score = db.Column(db.Float, nullable=False)
    reasons = db.Column(db.Text, nullable=True)
    questions = db.Column(db.Text, nullable=True)

@app.before_request
def create_tables():
    db.create_all()

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already exists!', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    total_interviews = Interview.query.count()
    completed_interviews = Interview.query.filter_by(status='Completed').count()
    pending_interviews = Interview.query.filter_by(status='Pending').count()

    now = datetime.utcnow()
    last_month = now - timedelta(days=30)

    total_last_month = Interview.query.filter(
        Interview.created_at >= last_month,
        Interview.created_at <= now
    ).count()

    completed_last_month = Interview.query.filter(
        Interview.created_at >= last_month,
        Interview.created_at <= now,
        Interview.status == 'Completed'
    ).count()

    pending_last_month = Interview.query.filter(
        Interview.created_at >= last_month,
        Interview.created_at <= now,
        Interview.status == 'Pending'
    ).count()

    def calculate_change(current, previous):
        if previous == 0:
            return 0
        return round(((current - previous) / previous) * 100, 0)

    total_change = calculate_change(total_interviews, total_last_month)
    completed_change = calculate_change(completed_interviews, completed_last_month)
    pending_change = calculate_change(pending_interviews, pending_last_month)

    recent_interviews = Interview.query.order_by(
        Interview.created_at.desc()
    ).limit(5).all()

    return render_template(
        'dashboard/dashboard_main.html',
        total_interviews=total_interviews,
        completed_interviews=completed_interviews,
        pending_interviews=pending_interviews,
        total_change=total_change,
        completed_change=completed_change,
        pending_change=pending_change,
        recent_interviews=recent_interviews,
        date_today=datetime.now().strftime('%b %d, %Y'),
        user=user
    )

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        if 'profilePicture' in request.files:
            file = request.files['profilePicture']
            if file and file.filename != '':
                try:
                    img_base64 = compress_and_convert_to_base64(file.stream)
                    user.profile_picture = img_base64
                    db.session.commit()
                    flash('Profile picture updated successfully!', 'success')
                except Exception as e:
                    flash('An error occurred while updating the profile picture.', 'error')

        if 'name' in request.form:
            name = request.form['name']
            if name != user.username:
                user.username = name
                db.session.commit()
                flash('Name updated successfully!', 'success')

        if 'currentPassword' in request.form and 'newPassword' in request.form and 'confirmPassword' in request.form:
            current_password = request.form['currentPassword']
            new_password = request.form['newPassword']
            confirm_password = request.form['confirmPassword']

            if check_password_hash(user.password, current_password):
                if new_password == confirm_password:
                    user.password = generate_password_hash(new_password)
                    db.session.commit()
                    flash('Password updated successfully!', 'success')
                else:
                    flash('New passwords do not match.', 'error')
            else:
                flash('Current password is incorrect.', 'error')

        return redirect(url_for('settings'))

    return render_template('dashboard/dashboard_settings.html', user=user)

@app.route("/interviews")
def interviews():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    interviews = Interview.query.filter_by(user_id=user_id).all()
    return render_template('dashboard/dashboard_interviews.html', user=user, interviews=interviews, date_today = datetime.utcnow().date())

@app.route('/help-center')
def helpcenter():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    return render_template('dashboard/dashboard_help_center.html', user=user)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        flash('Thank you for contacting us! We will respond soon.', 'success')
        return redirect(url_for('contact'))

    return render_template('dashboard/dashboard_contact.html', user=user)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        flash("Your password reset link has been sent to your email", "success")
        return redirect(url_for('login'))

    return render_template('forgot_password.html')
@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    total_interviews = Interview.query.count()
    completed_interviews = Interview.query.filter_by(status='Completed').count()
    scheduled_interviews = Interview.query.filter_by(status='Scheduled').count()
    pending_interviews = Interview.query.filter_by(status='Pending').count()

    # Recent interviews (latest 5)
    recent_interviews = Interview.query.order_by(Interview.created_at.desc()).limit(5).all()

    # Prepare data for monthly trends
    monthly_counts = (
        db.session.query(func.extract('month', Interview.created_at).label('month'), func.count(Interview.id))
        .group_by('month')
        .order_by('month')
        .all()
    )
    # Fill in months 1-12 to avoid missing months
    months_labels = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    monthly_data = [0]*12
    for month, count in monthly_counts:
        monthly_data[int(month)-1] = count

    # Completion rate over time (e.g., weekly in last month)
    from datetime import timedelta
    today = datetime.utcnow()
    week_labels = []
    completion_data = []
    for i in range(4, 0, -1):
        week_start = today - timedelta(days=i*7)
        week_end = week_start + timedelta(days=7)
        week_labels.append(f"Week {5-i}")
        total_week = Interview.query.filter(Interview.created_at.between(week_start, week_end)).count()
        completed_week = Interview.query.filter(Interview.created_at.between(week_start, week_end), Interview.status=='Completed').count()
        completion_rate = round((completed_week/total_week)*100,2) if total_week else 0
        completion_data.append(completion_rate)

    return render_template(
        'dashboard/dashboard_analytics.html',
        total_interviews=total_interviews,
        completed_interviews=completed_interviews,
        scheduled_interviews=scheduled_interviews,
        pending_interviews=pending_interviews,
        recent_interviews=recent_interviews,
        months_labels=months_labels,
        monthly_data=monthly_data,
        week_labels=week_labels,
        completion_data=completion_data,
        user=user
    )

@app.route('/create_interview', methods=['GET', 'POST'])
def create_interview():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        title = request.form.get('title')
        domain = request.form.get('domain')
        duration = request.form.get('duration')
        description = request.form.get('description')
        interview = Interview(
            user_id=user.id,
            title=title,
            domain=domain,
            duration=duration,
            description=description,
            status = "Pending"
        )
        db.session.add(interview)
        db.session.commit()

        flash('Interview created successfully!', 'success')
        return redirect(url_for('dashboard'))

    return redirect(url_for('dashboard'))

@app.route('/take_interview/<int:interview_id>')
def take_interview(interview_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    interview = Interview.query.get_or_404(interview_id)
    questions = json.loads(interview.questions)

    return render_template('dashboard/take_interview.html', interview=interview, questions=questions)

@app.route('/delete_interview/<int:interview_id>', methods=['POST'])
def delete_interview(interview_id):
    interview = Interview.query.get_or_404(interview_id)
    db.session.delete(interview)
    db.session.commit()
    flash('Interview deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)