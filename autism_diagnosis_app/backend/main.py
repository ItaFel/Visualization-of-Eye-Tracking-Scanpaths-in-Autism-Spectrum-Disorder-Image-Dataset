from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import shutil
import os
import uuid
from schemas import UserCreate, UserLogin, DiagnosisRequest, DiagnosisResult
from processing import process_video_to_scanpath
from inference import predict_autism_risk

from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Autism Diagnosis Eye-Tracking")

app.mount("/static", StaticFiles(directory="../frontend"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mock Database
users_db = {}
diagnosis_results = {}

from fastapi.responses import FileResponse

@app.get("/")
async def read_index():
    return FileResponse("../frontend/index.html")

@app.post("/register")
def register(user: UserCreate):
    if user.username in users_db:
        raise HTTPException(status_code=400, detail="User already exists")
    users_db[user.username] = {"password": user.password, "has_paid": False}
    return {"message": "User created successfully"}

@app.post("/login")
def login(user: UserLogin):
    if user.username not in users_db or users_db[user.username]["password"] != user.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": "mock-token", "username": user.username}

@app.post("/buy")
def buy_diagnosis(username: str):
    if username not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    users_db[username]["has_paid"] = True
    return {"message": "Payment successful. You can now start diagnosis."}

@app.post("/start_diagnosis")
def start_diagnosis(req: DiagnosisRequest):
    # Check if user paid
    # In a real app we'd check the token/user_id from auth
    # For simplicity assuming user_id is username
    return {"status": "ready", "instructions": "Please ensure good lighting. Place the child 50cm from screen..."}

async def process_diagnosis(video_path: str, diagnosis_id: str):
    print(f"Processing video {video_path} for diagnosis {diagnosis_id}")
    
    try:
        # 1. Video -> Scanpath
        scanpath = process_video_to_scanpath(video_path)
        
        # 2. Inference
        risk_level, score = predict_autism_risk(scanpath)
        
        recommendations = (
            "Based on the analysis, we recommend consulting a specialist for further evaluation."
            if risk_level == "High"
            else "The analysis did not detect significant indicators. Regular check-ups are recommended."
        )
        
        diagnosis_results[diagnosis_id] = {
            "risk_level": risk_level,
            "score": score,
            "recommendations": recommendations
        }
    except Exception as e:
        print(f"Error processing diagnosis {diagnosis_id}: {e}")
        diagnosis_results[diagnosis_id] = {
            "risk_level": "Error",
            "score": 0.0,
            "recommendations": "An error occurred during analysis. Please try again."
        }

@app.post("/upload_video")
async def upload_video(background_tasks: BackgroundTasks, username: str, file: UploadFile = File(...)):
    if username not in users_db: # or not users_db[username]["has_paid"]:
         # Relaxing check for testing
         pass

    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    diagnosis_id = str(uuid.uuid4())
    diagnosis_results[diagnosis_id] = "Processing"
    
    # Run processing in background
    background_tasks.add_task(process_diagnosis, file_path, diagnosis_id)
    
    return {"diagnosis_id": diagnosis_id, "message": "Video uploaded. Processing started."}

@app.get("/result/{diagnosis_id}")
def get_result(diagnosis_id: str):
    res = diagnosis_results.get(diagnosis_id)
    if not res:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    if res == "Processing":
        return {"status": "processing"}
    return res
