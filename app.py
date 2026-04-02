from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = "super_secret_key_change_this"

# ---------------- DB CONNECTION FUNCTION ----------------
def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="shivaniii",
        database="ngo_management"
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
            return redirect(url_for('login'))  # register ke baad login pe bhejo
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
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

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
def upload_photo():
    if 'user_id' not in session:
        return redirect('/login')

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
def make_donation():
    if 'user_id' not in session:
        return redirect('/login')

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
def donation_success():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('donation_success.html')

# ---------------- EDIT PROFILE ----------------
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect('/login')

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

        # Session update
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
