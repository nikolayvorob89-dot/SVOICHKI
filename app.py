from flask import Flask, render_template
from flask_socketio import SocketIO, send
import eventlet
import os

eventlet.monkey_patch()  # обязательно для WebSocket

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('message')
def handle_message(msg):
    send(msg, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # берем порт от Render
    socketio.run(app, host='0.0.0.0', port=port)
