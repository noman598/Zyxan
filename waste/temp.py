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

@app.post("/extract")
async def extract_file(file_list: FileList, db: Session = Depends(get_db)):

    results = []
    for filename in file_list.filenames:
        try:

            file_path = os.path.join(UPLOAD_DIR, filename)

            if not os.path.exists(file_path):
                # raise HTTPException(status_code = 400, detail = "File not found")
                results.append({
                    "filename": filename,
                    "status": "error",
                    "message": "File not found"
                })
                continue

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

            else:
                raise ValueError(f"Unsupported file type: {filename}")

            extracted_content =  text["content"]

            # increment the revision count and fetch the oldpayload
            revision_and_payload = get_revision(filename, db)
            # if revision_and_payload[0] > 1:
            old_payload = revision_and_payload[1]

            # print("Value",revision_and_payload[0])

            prompt = extracted_content + demand_prompt
            # return {"content":prompt}
            response =  get_deepseekR1_res(prompt)
            match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                
                file_record = db.query(User).filter(
                    User.filename == filename, User.request_id == file_list.request_id).first()

                #get the diff field using comparision
                if revision_and_payload[0] > 1 and old_payload:
                    diff_dict = get_diff_dict(old_payload, data)
                    file_record.diff = diff_dict


                # db_entry = User(payload = data)
                file_record.payload = data
                file_record.revision = revision_and_payload[0]
                
                # db.add(db_entry)
                db.commit()
                db.refresh(file_record)
                # return{"id":db_entry.id, "payload": db_entry.payload}

            


        except Exception as e:
            results.append({
                "filename": filename,
                "status":"Error",
                "message": str(e)
            })
            continue
            # return JSONResponse(content={"res": data})

        
    return {"results": results}