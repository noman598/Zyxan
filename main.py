from fastapi import FastAPI, UploadFile, File, HTTPException, status, Depends
from fastapi.responses import JSONResponse
import os
from typing import Optional
import PyPDF2
import docx
import json
import csv
from pdf2image import convert_from_path
from bs4 import BeautifulSoup #for html parsing
import pytesseract # For OCR in scanned PDFs


import re
import json
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import uuid



from app.models import User
from app.database import engine, get_db, Base, SessionLocal
from sqlalchemy.orm import Session
from app.schema import UserBase, UserResponse, DeleteRequest

Base.metadata.create_all(bind=engine)

app = FastAPI()

load_dotenv()
deepseekR1_api_key = os.getenv("deepseekR1_api_key")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR,exist_ok=True)
text = ""
ALLOWED_EXTENSTION = {"pdf", "docx", "json", "csv", "html"}
poppler_path = r"C:\Users\NOMAN KHAN\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin"
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

demand_prompt = '''Extract all important key-value pairs from the following text. Return the result as a clean JSON object. Only include relevant fields. Do not invent information.
For each key-value pair, include a "confidence" field (as a float between 0 and 1) representing how certain you are about the correctness of the extraction based on the text. '''




def is_allowed_file(filename: str) -> bool:
    return (
        "." in filename and 
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSTION
    )

@app.get("/")
def read_root():
    return {"message": "FastAPI is working!"}


#-------- Testing Database-------------

# @app.post("/user", response_model = UserResponse, status_code = status.HTTP_201_CREATED)
# def create_user(user:UserBase, db: Session = Depends(get_db)):
#     existing_user = db.query(User).filter(User.email == user.email).first()
#     if existing_user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Email already exists"
#         )
    
#     new_user = User(name = user.name, email = user.email)
#     db.add(new_user)
#     db.commit()
#     db.refresh(new_user)
#     return new_user

@app.get("/all", response_model=list[UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users


@app.post("/delete")
def delete_row(payload: DeleteRequest, db:Session = Depends(get_db)):
    users = db.query(User).filter(User.id == payload.id).first()
    if users:
        db.delete(users)
        db.commit()
        return {"message": f"User with id {payload.id} deleted successfully."}
    return {"error": f"User with id {payload.id} not found."}










# ---- upload endpoint ----
@app.post("/upload/")
async def upload_file(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    request_id = str(uuid.uuid4())
    file_ids = []

    for file in files:
        try:
            if not file.filename:
                raise HTTPException(status_code = 400, detail = "No file uploaded")
                # continue
            
            elif not is_allowed_file(file.filename):
                raise HTTPException(status_code = 400, detail = "File type not Allowed")

            file_location = os.path.join(UPLOAD_DIR, file.filename)

            with open(file_location, 'wb') as buffer:
                contents = await file.read()
                buffer.write(contents)


            file_id = str(uuid.uuid4())
            uploaded_time = datetime.utcnow()
            
            file_record = User(
                file_id = file_id,
                filename = file.filename,
                uploaded_by = 1,
                uploaded_time = uploaded_time,
                request_id=request_id

            )

            db.add(file_record)
            db.commit()
            db.refresh(file_record)

            file_ids.append(file_id)
            # return {
            #     "filename": file.filename,
            #     # "description": description,
            #     "content_type": file.content_type,
            #     "size": len(contents),
            #     "saved_to": file_location,
            #     "message": "File uploaded successfully"
            # }

        except Exception as e:
            print("Error:" , str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Error processing file: {str(e)}"
            )

    # return {"file_ids": file_ids}
    return{"content":"succefully uploaded"}

# id, filename, revision, data, diff, 


# --- Extract endpoint ----

@app.post("/extract/{filename}")
async def extract_file(filename:str, user: UserBase, db: Session = Depends(get_db)):
    file_path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code = 400, detail = "File not found")

    #extract based on filetype - 

    if filename.endswith(".pdf"):
        text =  await extract_pdf(file_path)

    elif filename.endswith(".docx"):
        text =  await extract_docx(file_path)

    elif filename.endswith(".json"):
        text =  await extract_json(file_path)

    elif filename.endswith(".csv"):
        text =  await extract_csv(file_path)

    elif filename.endswith(".html"):
        text =  await extract_html(file_path)

    extracted_content =  text["content"]

    prompt = extracted_content + demand_prompt
    # return {"content":prompt}
    response =  get_deepseekR1_res(prompt)
    match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
    if match:
        json_str = match.group(1)
        data = json.loads(json_str)
        
        db_entry = User(payload = data)
        db.add(db_entry)
        db.commit()
        db.refresh(db_entry)
        return{"id":db_entry.id, "payload": db_entry.payload}



        # return JSONResponse(content={"res": data})

    else:
        return{("No JSON found")}

#---------- DeepSeek API Connection -----------

def get_deepseekR1_res(message):
    client = OpenAI(
        api_key= deepseekR1_api_key,
        base_url="https://api.sambanova.ai/v1",
    )

    response = client.chat.completions.create(
        model="DeepSeek-R1",
        messages=[{"role":"system","content":"You are a helpful assistant"},
                  {"role":"user","content": message}],
        temperature=0.1,
        top_p=0.1
    )

    return response.choices[0].message.content



# ----Extract function ------

async def extract_pdf(file_path: str) -> dict:
    text = ""
    
    # if is_scanned:
    #     images = convert_from_path(file_path)
    #     for img in images:
    #         text += pytesseract.images_to_string(img) + "\n"
    
    with open(file_path, "rb") as file:
        reader  = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + "\n"

    if not text or len(text.strip()) < 10:
        text = ""
        try:

            images = convert_from_path(file_path, poppler_path = poppler_path)
            for img in images:
                text += pytesseract.image_to_string(img) + "\n"
        except Exception as e:
            print(f"error with ocr:{e}")

    return {"filename": os.path.basename(file_path), "content": text, "type": "pdf"}

async def extract_docx(file_path: str) -> dict:
    doc = docx.Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return {"filename": os.path.basename(file_path), "content": text, "type":"docx"}


async def extract_json(file_path:str) -> dict:
    text = ""
    with open(file_path, 'r') as file:
        text = json.load(file) #convert json format to dict or list format
    return {"filename": os.path.basename(file_path), "content": text, "type":"json"}

 
async def extract_csv(file_path: str) -> dict:
    text = ""
    with open(file_path, "r") as file:
        reader = csv.DictReader(file)
        text = [row for row in reader]
    return {"filename": os.path.basename(file_path), "content": text, "type":"json"}


async def extract_html(file_path: str) -> dict:
    with open(file_path, "r") as file:
        soup = BeautifulSoup(file.read(), "html.parser")
        text = soup.get_text()
    return {"filename": os.path.basename(file_path), "content": text, "type": "html"}



