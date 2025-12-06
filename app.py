from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = 'secret_key_for_session'

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
        else:
            return "Неверный логин или пароль"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')

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

@app.route('/chat/<username>', methods=['GET', 'POST'])
def chat_with(username):
    if 'username' not in session:
        return redirect('/login')
    if username == session['username']:
        return redirect('/users')

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        message = request.form['message']
        if message.strip() != '':
            c.execute('INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)',
                      (session['username'], username, message))
            conn.commit()
    conn.close()
    return render_template('chat.html', username=session['username'], chat_with=username)

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
    messages = c.fetchall()
    conn.close()
    messages_formatted = [f"{sender} : {message}" for sender, message in messages]
    return jsonify(messages_formatted)

if __name__ == '__main__':
    app.run(debug=True)
