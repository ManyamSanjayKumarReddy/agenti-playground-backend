from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class File(BaseModel):
    path: str = Field(description="The path of the file to be created or modified")
    purpose: str = Field(
        description=" THe purpose of the file eg the main application logic , data procession module , pipeline , global css"
    )

class Plan(BaseModel):
    name : str = Field(description='The name of the app to be built')
    description: str = Field(
        description="A Oneline description of the app to be built. e.g 'A web application for managing personal projects"
    )

    techstack: str = Field(
        description='the tech stack to be used in the app, e.g : PYthon, html , css , javascript , react , flask'
    )
    features : list[str] = Field(
        description="A list of features that app should have e.g. 'user authentication', 'data visualization'"
    )

    files: list[File] = Field(description="A list of Files to be created , with each path and purpose")

class ImplementationTask(BaseModel):
    filepath: str = Field(description="The path to the file to be modified")
    task_description: str = Field(
        description="A detailed description of the task to be performed on the file, e.g. 'add user authentication', 'implement data processing logic', etc."
    )

class TaskPlan(BaseModel):
    implementation_steps: list[ImplementationTask] = Field(description="A list of steps to be taken to implement the task")
    # model_config = ConfigDict(extra="allow")

class CoderState(BaseModel):
    task_plan: TaskPlan = Field(description="the plan for the task to be implemented")
    current_step_idx : int = Field(0, description="The index of the current step in the implementation steps")
    current_file_content: Optional[str] = Field(None, description="The content of the file currently being edited or created")

