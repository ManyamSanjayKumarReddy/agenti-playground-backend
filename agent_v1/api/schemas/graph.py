from pydantic import BaseModel, Field
from typing import List

class GenerateProjectRequest(BaseModel):
    prompt: str = Field(..., description="User prompt to generate the project")

class GenerateProjectResponse(BaseModel):
    project_name: str
    project_root: str

class ListFilesResponse(BaseModel):
    project_name: str
    files: List[str]

class ReadFileResponse(BaseModel):
    project_name: str
    file_path: str
    content: str

class WriteFileRequest(BaseModel):
    content: str
