import os
import re
import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI
from dotenv import load_dotenv
app = FastAPI()
# Load environment variables from .env file
load_dotenv()
deepseekR1_api_key = os.getenv("deepseekR1_api_key")

text = "John Doe was born on January 1st, 1990. He currently lives at 123 Elm Street, NY. You can contact him via john@example.com or call 555-1234."

demand_prompt = "Extract all important key-value pairs from the following text. Return the result as a clean JSON object. Only include relevant fields. Do not invent information."

@app.get("/")
def check():
    return {"content":"Hello"}

@app.get("/Home")
def get_pair():
    prompt = text + demand_prompt
    # return {"content":prompt}
    response =  get_deepseekR1_res(prompt)
    match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
    if match:
        json_str = match.group(1)
        data = json.loads(json_str)
        # return jsonify({"res":data})
        return JSONResponse(content={"res": data})

    else:
        return{("No JSON found")}



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