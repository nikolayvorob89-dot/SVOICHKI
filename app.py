from flask import Flask, render_template, request, redirect, session
from flask_socketio import SocketIO, join_room, emit
import os

app = Flask(__name__)
app.secret_key = "secretkey"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

users = {}            # username -> password
messages = {}         # ("u1","u2") -> list of messages


def room_name(u1, u2):
    return "_".join(sorted([u1, u2]))


@app.route('/')
def index():
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users and users[username] == password:
            session['username'] = username
            return redirect('/users')

        return "Неверный логин или пароль"

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users:
            return "Пользователь уже существует"

        users[username] = password
        session['username'] = username
        return redirect('/users')

    return render_template('register.html')


@app.route('/users')
def users_list():
    if "username" not in session:
        return redirect('/login')

    current = session['username']
    lst = [u for u in users if u != current]

    return render_template("users.html", users=lst)


@app.route('/chat/<username>')
def chat(username):
    if "username" not in session:
        return redirect('/login')

    me = session['username']
    room = room_name(me, username)
    msgs = messages.get(room, [])

    return render_template("chat.html",
                           username=me,
                           receiver=username,
                           messages=msgs)


# ==== SOCKET.IO ====


@socketio.on("join")
def on_join(data):
    room = room_name(data['sender'], data['receiver'])
    join_room(room)


@socketio.on("send_message")
def on_send(data):
    sender = data['sender']
    receiver = data['receiver']
    text = data['text']

    room = room_name(sender, receiver)

    if room not in messages:
        messages[room] = []

    messages[room].append((sender, text))

    emit("new_message", {"sender": sender, "text": text}, room=room)


@socketio.on("typing")
def on_typing(data):
    sender = data['sender']
    receiver = data['receiver']
    room = room_name(sender, receiver)

    emit("show_typing", {"sender": sender}, room=room)


@socketio.on("stop_typing")
def on_stop_typing(data):
    sender = data['sender']
    receiver = data['receiver']
    room = room_name(sender, receiver)

    emit("hide_typing", {"sender": sender}, room=room)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True)
