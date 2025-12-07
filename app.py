from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'
socketio = SocketIO(app, manage_session=False)

DB = 'users.db'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

# --- Helper функции ---
def get_users():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE username != ?", (session['username'],))
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def get_messages(user1, user2):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "SELECT sender, message FROM messages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC",
        (user1, user2, user2, user1)
    )
    msgs = c.fetchall()
    conn.close()
    return msgs

# --- Flask routes ---
@app.route('/')
def index():
    if 'username' not in session:
        return redirect('/login')
    users = get_users()
    return render_template('index.html', username=session['username'], users=users)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()
        if user and password == user[0]:
            session['username'] = username
            return redirect('/')
        else:
            return "Неверный логин или пароль"
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect('/login')
        except sqlite3.IntegrityError:
            return "Пользователь уже существует"
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')

# --- API для истории сообщений ---
@app.route('/messages/<receiver>')
def get_chat_history(receiver):
    if 'username' not in session:
        return jsonify([])
    msgs = get_messages(session['username'], receiver)
    return jsonify([{'sender': s, 'message': m} for s, m in msgs])

# --- Загрузка файлов ---
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'username' not in session or 'receiver' not in request.form:
        return "Unauthorized", 403
    if 'file' not in request.files:
        return "No file", 400
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return "Invalid file", 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename).replace("\\","/")
    file.save(filepath)

    sender = session['username']
    receiver = request.form['receiver']
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)", 
              (sender, receiver, f"/{filepath}"))
    conn.commit()
    conn.close()

    room = get_room_name(sender, receiver)
    socketio.emit('receive_message', {
        'sender': sender,
        'message': f"/{filepath}",
        'type':'image'
    }, room=room)
    return "OK", 200

# --- SocketIO ---
@socketio.on('join')
def handle_join(data):
    room = get_room_name(session['username'], data['receiver'])
    join_room(room)

@socketio.on('leave')
def handle_leave(data):
    room = get_room_name(session['username'], data['receiver'])
    leave_room(room)

@socketio.on('send_message')
def handle_message(data):
    sender = session['username']
    receiver = data['receiver']
    msg = data['message']
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)", (sender, receiver, msg))
    conn.commit()
    conn.close()
    
    room = get_room_name(sender, receiver)
    socketio.emit('receive_message', {'sender': sender, 'message': msg, 'type':'text'}, room=room)

@socketio.on('typing')
def handle_typing(data):
    sender = session['username']
    receiver = data['receiver']
    room = get_room_name(sender, receiver)
    emit('display_typing', {'sender': sender}, room=room, include_self=False)

def get_room_name(user1, user2):
    return '_'.join(sorted([user1, user2]))

if __name__ == '__main__':
    socketio.run(app, debug=True)
