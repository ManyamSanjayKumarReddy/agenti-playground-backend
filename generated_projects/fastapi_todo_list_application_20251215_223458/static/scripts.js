// JavaScript for frontend interactivity and API calls

// Function to fetch data from the API
async function fetchData(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('There has been a problem with your fetch operation:', error);
    }
}

// Example of using fetchData
async function loadTodos() {
    const todos = await fetchData('/api/todos');
    console.log(todos);
}

// Event listener for a button click to load todos
document.getElementById('load-todos-btn').addEventListener('click', loadTodos);

// Call loadTodos on page load
window.onload = loadTodos;