# backend/app/debug_main.py

import logging
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# --- A minimal FastAPI app for debugging CORS with file uploads ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

# Use the exact same CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/test-upload")
async def test_upload_endpoint(file: UploadFile = File(...)):
    """
    A dead-simple endpoint that only accepts a file and returns its name.
    We use the standard File() dependency to perfectly replicate the failing condition.
    """
    logging.info(f"Debug server received file: {file.filename}")
    return {"filename": file.filename, "content_type": file.content_type, "status": "success"}

@app.get("/")
def read_root():
    return {"message": "This is the DEBUG server."}