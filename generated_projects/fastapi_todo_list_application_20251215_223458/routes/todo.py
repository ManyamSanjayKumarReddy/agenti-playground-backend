from fastapi import APIRouter, HTTPException
from typing import List
from models import Todo
from schemas import TodoCreate, TodoUpdate

router = APIRouter()

todos = []  # This will act as our in-memory database for now

@router.post("/todos/", response_model=Todo)
async def create_todo(todo: TodoCreate):
    new_todo = Todo(id=len(todos) + 1, **todo.dict())
    todos.append(new_todo)
    return new_todo

@router.get("/todos/", response_model=List[Todo])
async def read_todos():
    return todos

@router.get("/todos/{todo_id}", response_model=Todo)
async def read_todo(todo_id: int):
    todo = next((todo for todo in todos if todo.id == todo_id), None)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo

@router.put("/todos/{todo_id}", response_model=Todo)
async def update_todo(todo_id: int, todo_update: TodoUpdate):
    todo = next((todo for todo in todos if todo.id == todo_id), None)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    for key, value in todo_update.dict().items():
        setattr(todo, key, value)
    return todo

@router.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int):
    global todos
    todos = [todo for todo in todos if todo.id != todo_id]
    return {"detail": "Todo deleted"}
