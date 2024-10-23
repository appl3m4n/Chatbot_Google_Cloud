from flask import Flask, render_template, request
from flask_mysqldb import MySQL
import json
from difflib import get_close_matches

app = Flask(__name__)

# Initialize Flask MySQL
app.config['MYSQL_HOST'] = "localhost"
app.config['MYSQL_USER'] = "root"
app.config['MYSQL_PASSWORD'] = ""
app.config['MYSQL_DB'] = "users_db"

#Google Cloud
#app.config['MYSQL_HOST'] = "/cloudsql/double-balm-433618-r6:us-central1:roman"
#app.config['MYSQL_USER'] = "roman"
#app.config['MYSQL_PASSWORD'] = "1994"
#app.config['MYSQL_DB'] = "users_db"


mysql = MySQL(app)

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

    # Assuming user details are collected from the form as well
    userDetails = {'name': request.form.get('name', 'Guest')}  # Example user detail

    # Store user input and model output in the database
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO users_gpt (input, output) VALUES (%s, %s)", (chatgpt_input, chatgpt_output))
    mysql.connection.commit()
    cur.close()

    # Fetch all data from the database
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users_gpt ORDER BY id DESC LIMIT 5")
    userDetails = cur.fetchall()
    cur.close()

    # Render the template with user input, model output, and user details
    return render_template('index_submit.html', chatgpt_input=chatgpt_input, chatgpt_output=chatgpt_output, userDetails=userDetails)

if __name__ == '__main__':
    app.run(debug=True)  # Set debug=True for easier development
