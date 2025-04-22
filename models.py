from pydantic import BaseModel
from typing import Optional
# c8ae0098-6fe3-47fc-9ace-af5718a30255
# Request model - used when a client sends data (like POST/PUT)
class Task(BaseModel):
    title:str
    description: Optional[str] = None
    completed: bool = False

# Response model - what we return to client (includes ID)
class TaskInDB(Task):
    id:int