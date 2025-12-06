function sendMessage() {
    let msg = document.getElementById('message').value;
    if(msg.trim() === '') return;
    let div = document.createElement('div');
    div.className = 'message self';
    div.innerText = msg;
    document.querySelector('.chat-window').appendChild(div);
    document.getElementById('message').value = '';
    document.querySelector('.chat-window').scrollTop = document.querySelector('.chat-window').scrollHeight;
}
