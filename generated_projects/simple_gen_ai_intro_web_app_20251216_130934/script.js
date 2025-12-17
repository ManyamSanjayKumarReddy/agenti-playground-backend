// script.js

// Function to display a greeting
function displayGreeting() {
    const greeting = 'Hello, welcome to our website!';
    document.getElementById('greeting').innerText = greeting;
}

// Function to change background color
function changeBackgroundColor(color) {
    document.body.style.backgroundColor = color;
}

// Event listeners for interactivity
document.addEventListener('DOMContentLoaded', () => {
    displayGreeting();
    document.getElementById('colorButton').addEventListener('click', () => {
        changeBackgroundColor('lightblue');
    });
});