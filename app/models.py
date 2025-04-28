from sqlalchemy import Column, Integer, String, JSON, DateTime
from .database import Base
from datetime import datetime
import uuid
# class User(Base):
#     __tablename__ = "users"
#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(100))
#     email = Column(String(100), unique=True, index=True)

class User(Base):
    __tablename__ = "last_table"
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String(100), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    uploaded_by = Column(Integer, default=1)
    uploaded_time = Column(DateTime, default=datetime.utcnow)
    request_id = Column(String(36))
    payload = Column(JSON)
    revision = Column(Integer, default=0)
    diff = Column(JSON)
    



