from fastapi import FastAPI, HTTPException #some of them class and some are function
from typing import List
from models import Task, TaskInDB

app = FastAPI()

# why using fastAPI --->
# to do the multiple task at once -> called Aynchronous 
# watch first section->
# https://www.youtube.com/watch?app=desktop&v=rvFsGRvj9jo
# qs-  flask vs fastapi?

# Create a simple API ---->
@app.get("/")
def read_root():
    return {"message": "FastAPI is working!"}

@app.get("/hello/{name}")
def say_hello(name: str):
    return {"greeting": f"Hello, {name}!"}


# <--------------------------------------------------------------------------->






tasks: list[TaskInDB] = []
next_id = 1
# difference between task = [] and task : list[TaskInDB] = []? ---->
'''
task = [] ==>
Python doesn't know (or care) what's going to be inside that list.
You can put anything in it: numbers, strings, objects, mixed types... no rules.

task : list[TaskInDB] ==>
It tells other developers:
“Hey! This list is supposed to contain only TaskInDB objects.”

example  - 
tasks: list[int] = []
tasks.append("hello")  # ❌ Warning from type checker: "str" is not "int"
'''


@app.post("/task", response_model = TaskInDB)
def create_task(task: Task):
    # def fun(p: r): this is type hinting, a way to tell that you expect p to be of type r.

    global next_id
    new_task = TaskInDB(id = next_id, **task.dict())
    tasks.append(new_task)
    next_id += 1
    return new_task
'''
task.dict() converts a Pydantic model into a standard dictionary.
**task.dict() uses to pass as argument to any function to create new instances.
'''

@app.get("/tasks",response_model = List[TaskInDB])
def get_all():
    return tasks
