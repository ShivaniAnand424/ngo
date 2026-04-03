from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ngo_jyeshtha_secret_2024')

# ---------------- LOGIN REQUIRED DECORATOR ----------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

# ---------------- DB CONNECTION FUNCTION ----------------
def get_db_connection():
    conn = mysql.connector.connect(
        host=os.environ.get('MYSQLHOST'),
        port=int(os.environ.get('MYSQLPORT', 3306)),
        user=os.environ.get('MYSQLUSER'),
        password=os.environ.get('MYSQLPASSWORD'),
        database=os.environ.get('MYSQLDATABASE')
    )
    return conn

# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template("index.html")

# ---------------- ABOUT ----------------
@app.route('/about')
def about():
    return render_template("about.html")

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (full_name, email, phone, password, role) VALUES (%s,%s,%s,%s,%s)",
                (full_name, email, phone, password, role)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('login'))
        except Exception as e:
            return f"Error: {str(e)}"

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['full_name'] = user['full_name']
            session['email'] = user['email']
            session['phone'] = user['phone']
            session['role'] = user['role']
            session['profile_photo'] = user.get('profile_photo')
            return redirect('/dashboard')
        else:
            return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role', '').lower()
    name = session.get('full_name', 'Member')

    if role == 'senior':
        return render_template('senior_dashboard.html', name=name)
    elif role == 'volunteer':
        return render_template('volunteer_dashboard.html', name=name)
    elif role == 'donor':
        return render_template('donor_dashboard.html', name=name)
    else:
        return redirect('/login')

# ---------------- UPLOAD PHOTO ----------------
@app.route('/upload_photo', methods=['POST'])
@login_required
def upload_photo():
    if 'photo' not in request.files:
        return redirect('/dashboard')

    file = request.files['photo']

    if file.filename == '':
        return redirect('/dashboard')

    if not file.filename.lower().endswith(('.jpg', '.jpeg')):
        return redirect('/dashboard')

    upload_folder = os.path.join('static', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)

    filename = f"user_{session['user_id']}.jpg"
    file.save(os.path.join(upload_folder, filename))

    session['profile_photo'] = filename

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET profile_photo = %s WHERE id = %s",
                   (filename, session['user_id']))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect('/dashboard')

# ---------------- MAKE DONATION ----------------
@app.route('/make_donation', methods=['POST'])
@login_required
def make_donation():
    amount = request.form.get('amount')
    purpose = request.form.get('purpose')
    payment_mode = request.form.get('payment_mode')
    message = request.form.get('message', '')

    if not amount or float(amount) <= 0:
        return redirect('/dashboard')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO donations (user_id, amount, purpose, payment_mode, message) VALUES (%s, %s, %s, %s, %s)",
        (session['user_id'], float(amount), purpose, payment_mode, message)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return redirect('/donation_success')

# ---------------- DONATION SUCCESS ----------------
@app.route('/donation_success')
@login_required
def donation_success():
    return render_template('donation_success.html')

# ---------------- SUBMIT SERVICE REQUEST ----------------
@app.route('/submit_request', methods=['POST'])
@login_required
def submit_request():
    service_type = request.form.get('service_type', '')
    description = request.form.get('description', '')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO service_requests (user_id, service_type, description) VALUES (%s, %s, %s)",
        (session['user_id'], service_type, description)
    )
    conn.commit()
    cursor.close()
    conn.close()

    flash('Your request has been submitted successfully!')
    return redirect('/dashboard')

# ---------------- MARK ATTENDANCE ----------------
@app.route('/mark_attendance', methods=['POST'])
@login_required
def mark_attendance():
    task_name = request.form.get('task_name', '')
    date = request.form.get('date', '')
    note = request.form.get('note', '')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO attendance (user_id, task_name, date, note) VALUES (%s, %s, %s, %s)",
        (session['user_id'], task_name, date, note)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return render_template('attendance_success.html')

# ---------------- EDIT PROFILE ----------------
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        conn = get_db_connection()
        cursor = conn.cursor()

        if new_password:
            if new_password != confirm_password:
                cursor.close()
                conn.close()
                return render_template('edit_profile.html', error='Passwords do not match!')
            hashed = generate_password_hash(new_password)
            cursor.execute(
                "UPDATE users SET full_name=%s, phone=%s, password=%s WHERE id=%s",
                (full_name, phone, hashed, session['user_id'])
            )
        else:
            cursor.execute(
                "UPDATE users SET full_name=%s, phone=%s WHERE id=%s",
                (full_name, phone, session['user_id'])
            )

        conn.commit()
        cursor.close()
        conn.close()

        session['full_name'] = full_name
        session['phone'] = phone

        return render_template('edit_profile.html', success='Profile updated successfully!')

    return render_template('edit_profile.html')

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)