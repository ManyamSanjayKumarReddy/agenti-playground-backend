# Todo List Application

## Introduction
This is a simple Todo List application that allows users to manage their tasks efficiently.

## Setup Instructions
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd simple_todo_list_application
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python app.py
   ```

## Usage Examples
- **Add a Todo**: To add a new task, use the following endpoint:
  - `POST /todos` with JSON body:
    ```json
    {
      "title": "Buy groceries",
      "completed": false
    }
    ```
- **Get all Todos**: To retrieve all tasks, send a GET request to:
  - `GET /todos`
- **Update a Todo**: To update an existing task, use:
  - `PUT /todos/{id}` with JSON body:
    ```json
    {
      "title": "Buy groceries",
      "completed": true
    }
    ```
- **Delete a Todo**: To remove a task, send a DELETE request to:
  - `DELETE /todos/{id}`

## License
This project is licensed under the MIT License.