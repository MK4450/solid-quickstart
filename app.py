from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
import sqlite3
import json
import time

app = Flask(__name__)
app.secret_key = 'regEWFfew@!!#3TRee'

# Database setup
DATABASE = 'chat.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                content TEXT NOT NULL
            )
        ''')
        conn.commit()

# Store online users
online_users = set()

# Routes
@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            if cursor.fetchone():
                return 'Username already exists!'
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
            user = cursor.fetchone()
            if user:
                session['username'] = username
                online_users.add(username)
                return redirect(url_for('chat'))
        return 'Invalid username or password!'
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'username' in session:
        online_users.remove(session['username'])
        session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html', username=session['username'])

@app.route('/send', methods=['POST'])
def send_message():
    if 'username' not in session:
        return 'Unauthorized', 401
    sender = session['username']
    content = request.json.get('message')
    if content:
        with get_db() as conn:
            conn.execute('INSERT INTO messages (sender, content) VALUES (?, ?)', (sender, content))
            conn.commit()
        return '', 204
    return 'Message is required', 400

@app.route('/stream')
def stream():
    def event_stream():
        last_id = 0
        while True:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM messages WHERE id > ?', (last_id,))
                messages = cursor.fetchall()
                for message in messages:
                    yield f"data: {json.dumps({'sender': message['sender'], 'content': message['content']})}\n\n"
                    last_id = message['id']
            time.sleep(0.1)
    return Response(event_stream(), content_type='text/event-stream')

@app.route('/online_users')
def get_online_users():
    return jsonify(list(online_users))

# Initialize the database
init_db()

if __name__ == '__main__':
    app.run(debug=True, threaded=True)