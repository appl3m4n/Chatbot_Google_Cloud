from flask import Flask, render_template, request
from flask_mysqldb import MySQL
import json
import os
import pymysql
from difflib import get_close_matches

app = Flask(__name__)

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

    if selected_option == 'option2':  # JSON based chatbot
        knowledge_base = load_knowledge_base("knowledge_base.json")
        best_match = find_best_match(chatgpt_input, [q["question"] for q in knowledge_base["questions"]])

        if best_match:
            answer = get_answer_for_question(best_match, knowledge_base)
            link = get_link_for_question(best_match, knowledge_base)
            chatgpt_output = f'{answer} Link: {link}' if link else answer
        else:
            chatgpt_output = 'I don\'t know the answer.'
    else:
        chatgpt_output = 'Model not selected.'

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