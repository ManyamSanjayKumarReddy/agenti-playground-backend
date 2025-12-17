from fastapi import FastAPI
from generated_projects.fastapi_todo_list_application_20251215_223458.routes import auth, todo

app = FastAPI()

app.include_router(auth.router)
app.include_router(todo.router)

@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI Todo application!"}
