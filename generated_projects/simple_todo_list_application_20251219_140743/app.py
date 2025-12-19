import streamlit as st

# Set the title of the app
st.title("AI Agent Interface")

# Sidebar for user input
st.sidebar.header("User Input")

# Text input for user query
user_query = st.sidebar.text_input("Enter your query:")

# Button to submit the query
if st.sidebar.button("Submit"):
    if user_query:
        # Placeholder for processing the query
        st.write(f"You entered: {user_query}")
        # Here you can add further logic to handle the query
    else:
        st.write("Please enter a query to submit.")

# Main content area
st.header("Responses")
# Placeholder for displaying AI responses
st.write("Responses will be displayed here.")

# Todo list functionality
st.sidebar.header("Todo List")

# Initialize session state for tasks if it doesn't exist
if 'tasks' not in st.session_state:
    st.session_state.tasks = []

# Text input for new task
new_task = st.sidebar.text_input("Add a new task:")

# Button to add task
if st.sidebar.button("Add Task"):
    if new_task:
        st.session_state.tasks.append(new_task)
        st.sidebar.success(f"Task added: {new_task}")
        st.sidebar.text_input("Add a new task:", value="")  # Clear input after adding
    else:
        st.sidebar.warning("Please enter a task to add.")

# Display the tasks
st.sidebar.header("Current Tasks")
for i, task in enumerate(st.session_state.tasks):
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        st.write(f"- {task}")
    with col2:
        if st.button("Delete", key=f"delete_{i}"):
            st.session_state.tasks.pop(i)
            st.sidebar.success(f"Task deleted: {task}")
        if st.button("Complete", key=i):
            st.session_state.tasks.pop(i)
            st.sidebar.success(f"Task completed: {task}")