from pydantic import BaseModel, EmailStr
from typing import Dict, Any, List
import uuid
# Base model shared across other models
class UserBase(BaseModel):
    payload: Dict[str, Any]

# Model for creating a user (request model)
class UserCreate(UserBase):
    pass

# Model for returning user data (response model)
class UserResponse(BaseModel):
    id : int

class DeleteRequest(BaseModel):
    id: int

class FileList(BaseModel):
    filenames: List[str]
    request_id: str = str(uuid.uuid4())



    model_config = {
        "from_attributes": True
    }


