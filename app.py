from flask import Flask, render_template, url_for, redirect, request, flash
from flask_mysqldb import MySQL
import json
import os
import pymysql
import openai
from difflib import get_close_matches

from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from flask_mysqldb import MySQL
import MySQLdb

app = Flask(__name__)

# OpenAI API key
str1 = 'sk-proj-Vbn3Wjz2xzY7khGJWJxasOD8xjJH39q63rqlE6KHISQMdYWVkS_'
str2 = '36EWwvVbrp8LGwn_poZyz7ZT3BlbkFJB_VX9c2D_kT2TQJvRYdm1F2RmItabpz4NxTuovFG9qK-'
str3 = 'x6c6zT_783BTo0Mf_rf6QiOizb7TEA'

#google cloud
#db_user = os.environ.get('CLOUD_SQL_USERNAME')
#db_password = os.environ.get('CLOUD_SQL_PASSWORD')
#db_name = os.environ.get('CLOUD_SQL_DATABASE_NAME')
#db_connection_name = os.environ.get('CLOUD_SQL_CONNECTION_NAME')

#localhost
db_user = "root"
db_password = ""
db_name = "users_db"
db_connection_name = "localhost"

print("Database User:", db_user)
print("Database Password:", '*' * len(db_password) if db_password else "No password provided")
print("Host:", db_name)
print("Database Name:", db_connection_name)

#mysql = MySQL(app)

app.config['SECRET_KEY'] = 'thisisasecretkey'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''  # Add your password if required
app.config['MYSQL_DB'] = 'users_db'

mysql = MySQL(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password


@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM login WHERE id = %s", (user_id,))
    user_data = cur.fetchone()
    cur.close()
    if user_data:
        return User(user_data['id'], user_data['username'], user_data['password'])
    return None


class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Register')

    def validate_username(self, username):
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM login WHERE username = %s", (username.data,))
        existing_user_username = cur.fetchone()
        cur.close()
        if existing_user_username:
            raise ValidationError('That username already exists. Please choose a different one.')


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM login WHERE username = %s", (form.username.data,))
        user_data = cur.fetchone()
        cur.close()
        if user_data and bcrypt.check_password_hash(user_data['password'], form.password.data):
            user = User(user_data['id'], user_data['username'], user_data['password'])
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template('login.html', form=form)


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    print(f"Current User ID: {current_user.id}")  # Log the current user's ID
    return render_template('index_open.html', username=current_user.username)



@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO login (username, password) VALUES (%s, %s)", (form.username.data, hashed_password))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


# Load knowledge base from JSON file
def load_knowledge_base(file_path: str):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print("Knowledge base file not found.")
        return {"questions": []}  # Return an empty structure to avoid crashes

# Find best match for user question
def find_best_match(user_question: str, questions: list[str]):
    matches = get_close_matches(user_question, questions, n=1, cutoff=0.6)
    return matches[0] if matches else None

# Get answer for a question from knowledge base
def get_answer_for_question(question: str, knowledge_base: dict):
    for q in knowledge_base["questions"]:
        if q["question"] == question:
            return q["answer"]
    return None

# Get link associated with a question from knowledge base
def get_link_for_question(question: str, knowledge_base: dict):
    for q in knowledge_base.get("questions", []):
        if q.get("question") == question:
            return q.get("link")
    return None

# Step 1 Route for rendering the form page
@app.route('/')
def index():
    return render_template('index_open.html')

# Step 2 Route for handling form submission
@app.route('/submit', methods=['POST'])
def submit():
    # Get user input from the form
    chatgpt_input = request.form['chatgpt']

    # Check which model is selected by the user
    selected_option = request.form['dropdownBox']

    if selected_option == 'option1':  # ChatGPT model
        # Initialize OpenAI
        openai.api_key = str1 + str2 + str3
        
        # Send user input to OpenAI for completion
        completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": chatgpt_input}])
        chatgpt_output = completion.choices[0].message.content
    elif selected_option == 'option2':  # JSON based chatbot
        knowledge_base = load_knowledge_base("knowledge_base.json")
        best_match = find_best_match(chatgpt_input, [q["question"] for q in knowledge_base["questions"]])

        if best_match:
            answer = get_answer_for_question(best_match, knowledge_base)
            link = get_link_for_question(best_match, knowledge_base)
            if link:
                chatgpt_output = f'{answer} Link: {link}'
            else:
                chatgpt_output = f'{answer}' # If link is missing or not defined
        else:
            chatgpt_output = 'I don\'t know the answer.'
    else:
        chatgpt_output = 'Model not selected'

    if os.environ.get('GAE_ENV') == 'standard':
        # If deployed, use the local socket interface for accessing Cloud SQL
        unix_socket = '/cloudsql/{}'.format(db_connection_name)
        cnx = pymysql.connect(user=db_user, password=db_password,
                              unix_socket=unix_socket, db=db_name)
    else:
        # If running locally, use the TCP connections instead
        # Set up Cloud SQL Proxy (cloud.google.com/sql/docs/mysql/sql-proxy)
        # so that your application can use 127.0.0.1:3306 to connect to your
        # Cloud SQL instance
        host = '127.0.0.1'
        cnx = pymysql.connect(user=db_user, password=db_password,
                              host=host, db=db_name)

    userDetails = []

    try:
        with cnx.cursor() as cursor:
            # Insert user input and model output into the database
            cursor.execute("INSERT INTO users_gpt (input, output) VALUES (%s, %s)", 
                           (chatgpt_input, chatgpt_output))
            cnx.commit()  # Commit the transaction

            # Fetch all data from the database
            cursor.execute("SELECT * FROM users_gpt ORDER BY id DESC LIMIT 5")
            userDetails = cursor.fetchall()  # Fetch results

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
    finally:
        cnx.close()  # Ensure the connection is closed
        
    # Render the template with user input, model output, and user details
    return render_template('index_submit.html', chatgpt_input=chatgpt_input, chatgpt_output=chatgpt_output, userDetails=userDetails)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)