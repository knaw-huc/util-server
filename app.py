from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import hashlib
import uuid

app = FastAPI()
app.mount("/static", StaticFiles(directory="tmp"), name="static")

@app.get("/md5/{text}")
@app.get("/md5")
def generate_md5(text: str | None, q: str | None = Query(None, alias="text")):
    if q and q != "":
        text = q
    md5_hash = hashlib.md5(text.encode()).hexdigest()
    return {"md5": md5_hash}

@app.get("/uuid")
def generate_uuid():
    return {"uuid": str(uuid.uuid4())}

# @app.get("/files")
# def serve_file(file_path: str = Query(..., description="Path to the file")):
#     try:
#         with open(file_path, 'rb') as file:
#             content = file.read()
#         return {"file_content": content.decode('utf-8')}
#     except Exception as e:
#         return {"error": str(e)}
