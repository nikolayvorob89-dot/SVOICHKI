from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, emit, join_room
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "super_secret_key"

socketio = SocketIO(app)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

users_db = {}
messages = {}

def room_id(u1, u2):
    return "_".join(sorted([u1, u2]))

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ======== РЕГИСТРАЦИЯ ========
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        if username == "":
            return render_template("register.html", error="Имя пустое")
        if username in users_db:
            return render_template("register.html", error="Пользователь уже существует")

        password = request.form.get("password").strip()
        users_db[username] = password
        session["username"] = username
        return redirect("/users")

    return render_template("register.html")

# ======== ЛОГИН ========
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        if username in users_db and users_db[username] == password:
            session["username"] = username
            return redirect("/users")
        return render_template("login.html", error="Неверный логин или пароль")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/users")
def users():
    if "username" not in session:
        return redirect("/login")
    current = session["username"]
    users_list = [u for u in users_db.keys() if u != current]
    return render_template("users.html", users=users_list)

@app.route("/chat/<username>")
def chat(username):
    if "username" not in session:
        return redirect("/login")
    me = session["username"]
    r = room_id(me, username)
    chat_messages = messages.get(r, [])
    return render_template("chat.html", me=me, other=username, chat_messages=chat_messages)

@app.route("/upload_image", methods=["POST"])
def upload_image():
    if "username" not in session:
        return "NO", 403
    me = session["username"]
    other = request.form["other"]
    if "file" not in request.files:
        return "NOFILE", 400
    file = request.files["file"]
    if file.filename == "":
        return "EMPTY", 400
    if not allowed_file(file.filename):
        return "BADTYPE", 400
    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)
    img_url = "/static/uploads/" + filename
    r = room_id(me, other)
    msg = {"sender": me, "type": "image", "url": img_url}
    messages.setdefault(r, []).append(msg)
    socketio.emit("new_message", msg, room=r)
    return "OK"

# ======== SOCKET.IO ========
@socketio.on("join")
def join(data):
    join_room(data["room"])

@socketio.on("message")
def handle_msg(data):
    sender = data["sender"]
    receiver = data["receiver"]
    text = data["text"]
    r = room_id(sender, receiver)
    msg = {"sender": sender, "type": "text", "text": text}
    messages.setdefault(r, []).append(msg)
    emit("new_message", msg, room=r)

@socketio.on("typing")
def handle_typing(data):
    emit("typing_status", data, room=data["room"], include_self=False)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
