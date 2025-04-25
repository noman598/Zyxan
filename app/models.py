from sqlalchemy import Column, Integer, String, JSON
from .database import Base

# class User(Base):
#     __tablename__ = "users"
#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(100))
#     email = Column(String(100), unique=True, index=True)

class User(Base):
    __tablename__ = "json_data"
    id = Column(Integer, primary_key=True, index=True)
    payload = Column(JSON)



