from flask import Flask, render_template, request, redirect, url_for
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

app = Flask(__name__)

# OpenAI API key
str1 = 'sk-proj-Vbn3Wjz2xzY7khGJWJxasOD8xjJH39q63rqlE6KHISQMdYWVkS_'
str2 = '36EWwvVbrp8LGwn_poZyz7ZT3BlbkFJB_VX9c2D_kT2TQJvRYdm1F2RmItabpz4NxTuovFG9qK-'
str3 = 'x6c6zT_783BTo0Mf_rf6QiOizb7TEA'

# Database configuration
db_user = "root"
db_password = ""
db_name = "users_db"
db_connection_name = "localhost"

app.config['SECRET_KEY'] = 'thisisasecretkey'
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Helper function to get database connection
def get_db_connection():
    return pymysql.connect(
        host='127.0.0.1',
        user=db_user,
        password=db_password,
        db=db_name,
        cursorclass=pymysql.cursors.DictCursor
    )

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM login WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
        if user_data:
            return User(user_data['id'], user_data['username'], user_data['password'])
    finally:
        connection.close()
    return None

# RegisterForm class
class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Register')

    def validate_username(self, username):
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM login WHERE username = %s", (username.data,))
                existing_user = cursor.fetchone()
            if existing_user:
                raise ValidationError('That username already exists. Please choose a different one.')
        finally:
            connection.close()

# LoginForm class
class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Login')

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM login WHERE username = %s", (form.username.data,))
                user_data = cursor.fetchone()
            if user_data and bcrypt.check_password_hash(user_data['password'], form.password.data):
                user = User(user_data['id'], user_data['username'], user_data['password'])
                login_user(user)
                return redirect(url_for('index'))
        finally:
            connection.close()
    return render_template('login.html', form=form)

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
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO login (username, password) VALUES (%s, %s)", (form.username.data, hashed_password))
                connection.commit()
        finally:
            connection.close()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# Load knowledge base from JSON file
def load_knowledge_base(file_path: str):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {"questions": []}

# Utility functions for knowledge base matching
def find_best_match(user_question: str, questions: list[str]):
    matches = get_close_matches(user_question, questions, n=1, cutoff=0.6)
    return matches[0] if matches else None

def get_answer_for_question(question: str, knowledge_base: dict):
    for q in knowledge_base["questions"]:
        if q["question"] == question:
            return q["answer"]
    return None

def get_link_for_question(question: str, knowledge_base: dict):
    for q in knowledge_base["questions"]:
        if q["question"] == question:
            return q.get("link")
    return None

# Routes for OpenAI integration
@app.route('/')
def index():
    return render_template('index_open.html')

@app.route('/submit', methods=['POST'])
def submit():
    chatgpt_input = request.form['chatgpt']
    selected_option = request.form['dropdownBox']
    chatgpt_output = ""

    if selected_option == 'option1':  # OpenAI ChatGPT model
        openai.api_key = str1 + str2 + str3
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": chatgpt_input}]
        )
        chatgpt_output = completion.choices[0].message.content
    elif selected_option == 'option2':  # JSON-based chatbot
        knowledge_base = load_knowledge_base("knowledge_base.json")
        best_match = find_best_match(chatgpt_input, [q["question"] for q in knowledge_base["questions"]])

        if best_match:
            answer = get_answer_for_question(best_match, knowledge_base)
            chatgpt_output = answer or 'I don\'t know the answer.'
        else:
            chatgpt_output = 'I don\'t know the answer.'
    else:
        chatgpt_output = 'Model not selected'

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO users_gpt (input, output) VALUES (%s, %s)", (chatgpt_input, chatgpt_output))
            connection.commit()

            # Retrieve last 5 entries
            cursor.execute("SELECT * FROM users_gpt ORDER BY id DESC LIMIT 5")
            userDetails = cursor.fetchall()
    finally:
        connection.close()

    return render_template(
        'index_submit.html',
        chatgpt_input=chatgpt_input,
        chatgpt_output=chatgpt_output,
        userDetails=userDetails
    )

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
