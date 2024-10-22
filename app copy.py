from flask import Flask, render_template, request
from flask_mysqldb import MySQL
import openai
import json
from difflib import get_close_matches

app = Flask(__name__)

# Initialize Flask MySQL
app.config['MYSQL_HOST'] = "localhost"
app.config['MYSQL_USER'] = "root"
app.config['MYSQL_PASSWORD'] = ""
app.config['MYSQL_DB'] = "users_db"
mysql = MySQL(app)

# OpenAI API key
str1 = 'sk-6DurzFcba69Gqq8KkZeAT3B'
str2 = 'lbkFJYWeBEwHHM'
str3 = 'JVnBzt79unM'

# Load knowledge base from JSON file
def load_knowledge_base(file_path: str) -> dict:
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

# Find best match for user question
def find_best_match(user_question: str, questions: list[str]) -> str | None:
    matches = get_close_matches(user_question, questions, n=1, cutoff=0.6)
    return matches[0] if matches else None

# Get answer for a question from knowledge base
def get_answer_for_question(question: str, knowledge_base: dict) -> str | None:
    for q in knowledge_base["questions"]:
        if q["question"] == question:
            return q["answer"]
    return None

# Get link associated with a question from knowledge base
def get_link_for_question(question: str, knowledge_base: dict) -> str | None:
    for q in knowledge_base.get("questions", []):
        if q.get("question") == question:
            return q.get("link")
    return None

# Step 1 Route for rendering the form page and displaying SQL table
@app.route('/')
def index():
    return render_template('index_open.html')

# Step 2Route for handling form submission
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

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0')