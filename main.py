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
from app.schema import UserBase, UserResponse, DeleteRequest, FileList

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





@app.post("/upload-and-extract/")
async def upload_and_extract(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    request_id = str(uuid.uuid4())
    results = []

    for file in files:
        try:
            if not file.filename:
                raise HTTPException(status_code=400, detail="No file uploaded")

            if not is_allowed_file(file.filename):
                raise HTTPException(status_code=400, detail="File type not allowed")

            # Save file locally
            file_location = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_location, 'wb') as buffer:
                contents = await file.read()
                buffer.write(contents)

            # Extract content
            if file.filename.endswith(".pdf"):
                text = await extract_pdf(file_location)
            elif file.filename.endswith(".docx"):
                text = await extract_docx(file_location)
            elif file.filename.endswith(".json"):
                text = await extract_json(file_location)
            elif file.filename.endswith(".csv"):
                text = await extract_csv(file_location)
            elif file.filename.endswith(".html"):
                text = await extract_html(file_location)
            else:
                raise ValueError(f"Unsupported file type: {file.filename}")

            extracted_content = text["content"]

            # Fetch revision and old payload
            revision, old_payload = get_revision(file.filename, db)

            # Prepare prompt and get response
            prompt = extracted_content + demand_prompt
            response = get_deepseekR1_res(prompt)

            match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if not match:
                raise ValueError("No valid JSON found in model response")
            data = json.loads(match.group(1))

            # Calculate diff if needed
            diff_dict = None
            if revision > 1 and old_payload:
                print("hello")
                diff_dict = get_diff_dict(old_payload, data)
                print(diff_dict)

            # NOW create full DB record at once
            file_record = User(
                file_id=str(uuid.uuid4()),
                filename=file.filename,
                uploaded_by=1,  # Replace with dynamic user ID if needed
                uploaded_time=datetime.utcnow(),
                request_id=request_id,
                payload=data,
                revision=revision,
                diff=diff_dict
            )

            db.add(file_record)
            db.commit()
            db.refresh(file_record)

            results.append({
                "filename": file.filename,
                "status": "success",
                "message": "Uploaded and extracted successfully"
            })

        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "message": str(e)
            })

    return {
        "request_id": request_id,
        "results": results
    }




#----------- fetch the detail of table -------------

@app.get("/requests/")
def get_requests(db: Session = Depends(get_db)):
    records = db.query(User).all()
    return [
        {
            "request_id": record.request_id,
            "uploaded_by": record.uploaded_by,
            "uploaded_time": record.uploaded_time
        }
        for record in records
    ]


@app.get("/request-details/{request_id}")
def get_request_details(request_id: str, db: Session = Depends(get_db)):
    record = db.query(User).filter(User.request_id == request_id).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Request ID not found")
    
    return {
        "payload": record.payload,
        "diff": record.diff
    }



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





def get_revision(filename: str, db:Session) -> list:
    latest_file = db.query(User).filter(User.filename == filename).order_by(User.revision.desc()).first()

    

#    #two API code -  
#     if latest_file:
#         new_revision = latest_file.revision + 1

#         if new_revision == 1:
#             return [1, None]
#         else:
#             return [new_revision, latest_file.payload]



 # single API code - 
    if latest_file:
        new_revision = latest_file.revision + 1
    else:
        new_revision = 1

    return [new_revision, latest_file.payload if latest_file else None]




def get_diff_dict(old_data: dict, new_data: dict) -> dict:
    diff = {}
    for key , new_val in new_data.items():
        if key not in old_data:
            diff[key] = {"old": None, "new": new_val}
        elif str(old_data[key])!=  str(new_val):
            diff[key] = {"old": old_data[key], "new": new_val}
        
    for key in old_data.keys():
        if key not in new_data:
            diff[key] = {"old": old_data[key], "new": None}

    return diff

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



