from fastapi import FastAPI, UploadFile, File, HTTPException
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



app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR,exist_ok=True)

ALLOWED_EXTENSTION = {"pdf", "docx", "json", "csv", "html"}
poppler_path = r"C:\Users\NOMAN KHAN\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin"
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def is_allowed_file(filename: str) -> bool:
    return (
        "." in filename and 
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSTION
    )

@app.get("/")
def read_root():
    return {"message": "FastAPI is working!"}

# ---- upload endpoint ----
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        if not file.filename:
            raise HTTPException(status_code = 400, detail = "No file uploaded")
        
        elif not is_allowed_file(file.filename):
            raise HTTPException(status_code = 400, detial = "File type not Allowed")

        file_location = os.path.join(UPLOAD_DIR, file.filename)

        with open(file_location, 'wb') as buffer:
            contents = await file.read()
            buffer.write(contents)
        
        return {
            "filename": file.filename,
            # "description": description,
            "content_type": file.content_type,
            "size": len(contents),
            "saved_to": file_location,
            "message": "File uploaded successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )


# --- Extract endpoint ----

@app.get("/extract/{filename}")
async def extract_file(filename:str):
    file_path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code = 400, detail = "File not found")

    #extract based on filetype - 

    if filename.endswith(".pdf"):
        return await extract_pdf(file_path)

    elif filename.endswith(".docx"):
        return await extract_docx(file_path)

    elif filename.endswith(".json"):
        return await extract_json(file_path)

    elif filename.endswith(".csv"):
        return await extract_csv(file_path)

    elif filename.endswith(".html"):
        return await extract_html(file_path)

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
