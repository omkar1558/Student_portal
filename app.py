from flask import Flask, request, jsonify, session, redirect, url_for, render_template, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Email, NumberRange
from flask_wtf.csrf import CSRFProtect
import mysql.connector
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = '123'

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Database connection configuration
db_config = {
    'user': 'root',
    'password': 'Omkar28012001#',
    'host': '127.0.0.1',
    'database': 'student_portal'
}

# Database connection function
def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn

def login_required(role):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if role == 'admin' and session.get('role') != 'admin':
                return redirect(url_for('login'))
            elif role == 'student' and session.get('role') != 'student':
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    class LoginForm(FlaskForm):
        username = StringField('Username', validators=[DataRequired()])
        password = PasswordField('Password', validators=[DataRequired()])
        submit = SubmitField('Login')

    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check student credentials
        cursor.execute("SELECT * FROM student_credentials WHERE username = %s AND password = %s", (username, password))
        student = cursor.fetchone()

        if student:
            session['user_id'] = student['prn_no']
            session['role'] = 'student'
            cursor.close()
            conn.close()
            return redirect(url_for('student_dashboard'))

        # Check admin credentials
        cursor.execute("SELECT * FROM admin_credentials WHERE username = %s AND password = %s", (username, password))
        admin = cursor.fetchone()

        if admin:
            session['user_id'] = admin['id']
            session['role'] = 'admin'
            cursor.close()
            conn.close()
            return redirect(url_for('admin_dashboard'))

        cursor.close()
        conn.close()
        return jsonify({'message': 'Invalid credentials'}), 401

    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/student/dashboard')
@login_required('student')
def student_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT s.prn_no, s.name, s.email, s.course, m.linux, m.python, m.dbms, m.big_data, m.java, m.machine_learning, m.data_visualization "
        "FROM students s "
        "JOIN marks m ON s.prn_no = m.prn_no WHERE s.prn_no = %s", 
        (session['user_id'],)
    )
    student = cursor.fetchone()

    # Calculate rank in class based on total marks
    cursor.execute("SELECT prn_no, (linux + python + dbms + big_data + java + machine_learning + data_visualization) as total_marks FROM marks")
    all_students = cursor.fetchall()
    all_students.sort(key=lambda x: x['total_marks'], reverse=True)
    rank_list = [i+1 for i, s in enumerate(all_students) if s['prn_no'] == student['prn_no']]
    rank = rank_list[0] if rank_list else None

    cursor.close()
    conn.close()
    return render_template('student_dashboard.html', student=student, rank=rank)

@app.route('/admin/dashboard')
@login_required('admin')
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT s.prn_no, s.name, s.email, s.course FROM students s")
    students = cursor.fetchall()

    # Calculate rank in class for each student
    cursor.execute("SELECT prn_no, (linux + python + dbms + big_data + java + machine_learning + data_visualization) as total_marks FROM marks")
    all_students = cursor.fetchall()
    all_students.sort(key=lambda x: x['total_marks'], reverse=True)
    for student in students:
        rank_list = [i+1 for i, s in enumerate(all_students) if s['prn_no'] == student['prn_no']]
        student['rank'] = rank_list[0] if rank_list else None

    cursor.close()
    conn.close()
    return render_template('admin_dashboard.html', students=students)

@app.route('/add_student', methods=['GET', 'POST'])
@login_required('admin')
def add_student():
    class AddStudentForm(FlaskForm):
        prn_no = StringField('PRN No', validators=[DataRequired()])
        name = StringField('Name', validators=[DataRequired()])
        email = StringField('Email', validators=[DataRequired(), Email()])
        course = StringField('Course', validators=[DataRequired()])
        submit = SubmitField('Add Student')

    form = AddStudentForm()

    if form.validate_on_submit():
        prn_no = form.prn_no.data
        name = form.name.data
        email = form.email.data
        course = form.course.data

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO students (prn_no, name, email, course) VALUES (%s, %s, %s, %s)", 
            (prn_no, name, email, course)
        )
        cursor.execute(
            "INSERT INTO marks (prn_no) VALUES (%s)",
            (prn_no,)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('admin_dashboard'))

    return render_template('add_student.html', form=form)

@app.route('/edit_student/<prn_no>', methods=['GET', 'POST'])
@login_required('admin')
def edit_student(prn_no):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students WHERE prn_no = %s", (prn_no,))
    student = cursor.fetchone()
    cursor.close()
    conn.close()

    if not student:
        return redirect(url_for('admin_dashboard'))

    class EditStudentForm(FlaskForm):
        prn_no = StringField('PRN No', validators=[DataRequired()], default=student['prn_no'])
        name = StringField('Name', validators=[DataRequired()], default=student['name'])
        email = StringField('Email', validators=[DataRequired(), Email()], default=student['email'])
        course = StringField('Course', validators=[DataRequired()], default=student['course'])
        submit = SubmitField('Edit Student')

    form = EditStudentForm()

    if form.validate_on_submit():
        prn_no = form.prn_no.data
        name = form.name.data
        email = form.email.data
        course = form.course.data

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE students SET name = %s, email = %s, course = %s WHERE prn_no = %s", 
            (name, email, course, prn_no)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_student.html', form=form)

@app.route('/delete_student/<prn_no>', methods=['GET', 'POST'])
@login_required('admin')
def delete_student(prn_no):
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM students WHERE prn_no = %s", (prn_no,))
        cursor.execute("DELETE FROM marks WHERE prn_no = %s", (prn_no,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('admin_dashboard'))
    else:
        return render_template('delete_student.html')


@app.route('/view_marks/<prn_no>')
@login_required('student')
def view_marks(prn_no):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM marks WHERE prn_no = %s", (prn_no,))
    marks = cursor.fetchone()
    cursor.close()
    conn.close()

    if not marks:
        flash("Marks not found for the given PRN.")
        return redirect(url_for('student_dashboard'))

    return render_template('view_marks.html', marks=marks)

@app.route('/edit_marks/<prn_no>', methods=['GET', 'POST'])
@login_required('admin')
def edit_marks(prn_no):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM marks WHERE prn_no = %s", (prn_no,))
    marks = cursor.fetchone()
    cursor.close()
    conn.close()

    if not marks:
        flash("Marks not found for the given PRN.")
        return redirect(url_for('admin_dashboard'))

    class EditMarksForm(FlaskForm):
        linux = IntegerField('Linux', validators=[DataRequired(), NumberRange(min=0, max=100)], default=marks['linux'])
        python = IntegerField('Python', validators=[DataRequired(), NumberRange(min=0, max=100)], default=marks['python'])
        dbms = IntegerField('DBMS', validators=[DataRequired(), NumberRange(min=0, max=100)], default=marks['dbms'])
        big_data = IntegerField('Big Data', validators=[DataRequired(), NumberRange(min=0, max=100)], default=marks['big_data'])
        java = IntegerField('Java', validators=[DataRequired(), NumberRange(min=0, max=100)], default=marks['java'])
        machine_learning = IntegerField('Machine Learning', validators=[DataRequired(), NumberRange(min=0, max=100)], default=marks['machine_learning'])
        data_visualization = IntegerField('Data Visualization', validators=[DataRequired(), NumberRange(min=0, max=100)], default=marks['data_visualization'])
        submit = SubmitField('Edit Marks')

    form = EditMarksForm()

    if form.validate_on_submit():
        linux = form.linux.data
        python = form.python.data
        dbms = form.dbms.data
        big_data = form.big_data.data
        java = form.java.data
        machine_learning = form.machine_learning.data
        data_visualization = form.data_visualization.data

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE marks SET linux = %s, python = %s, dbms = %s, big_data = %s, java = %s, machine_learning = %s, data_visualization = %s WHERE prn_no = %s",
            (linux, python, dbms, big_data, java, machine_learning, data_visualization, prn_no)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_marks.html', form=form)

if __name__ == '__main__':
    app.run(debug=True)
