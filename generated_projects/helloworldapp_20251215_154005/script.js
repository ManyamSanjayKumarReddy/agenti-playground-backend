// script.js

function displayMessage() {
    const message = 'Hello, World!';
    const messageElement = document.createElement('div');
    messageElement.textContent = message;
    document.body.appendChild(messageElement);
}

window.onload = displayMessage;