from pydantic import BaseModel

# Request schema for creating a resource
class CreateResourceRequest(BaseModel):
    name: str
    description: str
    quantity: int

# Response schema for returning a resource
class ResourceResponse(BaseModel):
    id: int
    name: str
    description: str
    quantity: int
    created_at: str
