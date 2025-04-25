from pydantic import BaseModel, EmailStr
from typing import Dict, Any

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

    
    model_config = {
        "from_attributes": True
    }


