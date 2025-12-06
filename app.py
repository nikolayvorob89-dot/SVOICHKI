from flask import Flask, render_template, request, redirect, session, jsonify
from flask_socketio import SocketIO, emit, join_room
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'secret_key_for_session'
socketio = SocketIO(app, cors_allowed_origins="*")

# ---- DATABASE ----
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            message TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ---- DEFAULT ROUTE ----
@app.route('/')
def index():
    return redirect('/login')

# ---- AUTH ----
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Пользователь уже существует"
        conn.close()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['username'] = username
            return redirect('/users')
        return "Неверный логин или пароль"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')

# ---- USERS ----
@app.route('/users')
def users():
    if 'username' not in session:
        return redirect('/login')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE username != ?', (session['username'],))
    users_list = [row[0] for row in c.fetchall()]
    conn.close()
    return render_template('users.html', users=users_list)

# ---- CHAT PAGE ----
@app.route('/chat/<username>')
def chat(username):
    if 'username' not in session:
        return redirect('/login')
    if username == session['username']:
        return redirect('/users')

    return render_template('chat.html', username=session['username'], chat_with=username)

# FETCH HISTORY
@app.route('/messages/<username>')
def get_messages(username):
    if 'username' not in session:
        return jsonify([])

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        SELECT sender, message FROM messages
        WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
        ORDER BY id
    ''', (session['username'], username, username, session['username']))
    rows = c.fetchall()
    conn.close()

    formatted = [f"{s} : {m}" for s, m in rows]
    return jsonify(formatted)

# ---- SOCKETIO ----

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)

@socketio.on('send_message')
def handle_message(data):
    sender = data['sender']
    receiver = data['receiver']
    message = data['message']

    # save to DB
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)',
              (sender, receiver, message))
    conn.commit()
    conn.close()

    room = f"room_{min(sender, receiver)}_{max(sender, receiver)}"
    emit('new_message', f"{sender} : {message}", room=room)

@socketio.on('typing')
def on_typing(data):
    sender = data['sender']
    receiver = data['receiver']

    room = f"room_{min(sender, receiver)}_{max(sender, receiver)}"

    emit('typing_status', f"{sender} печатает…", room=room, include_self=False)

# ---- RUN ----
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
