# routes/emotions.py
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from db.mongo import DatabaseConnection
from routes.users import get_current_user
import cv2
import numpy as np
from datetime import datetime
import tempfile
import os
from typing import List

router = APIRouter()

# Initialize face detection classifier
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

async def analyze_emotion(face_image) -> dict:
    # Basic emotion analysis based on facial features
    # This is a simplified version - you may want to enhance this
    try:
        gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        # Basic emotion scores based on image properties
        brightness = np.mean(gray)
        contrast = np.std(gray)
        
        # Simple scoring logic (this is just an example - you should adapt this)
        scores = {
            "neutral": 0.5,
            "happy": max(0, min(1, brightness / 255)),
            "sad": max(0, min(1, 1 - brightness / 255)),
            "surprise": max(0, min(1, contrast / 128))
        }
        return scores
    except Exception as e:
        print(f"Error in emotion analysis: {str(e)}")
        return {}

async def process_image(image_data) -> dict:
    try:
        gray = cv2.cvtColor(image_data, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) > 0:
            # Process the first detected face
            x, y, w, h = faces[0]
            face_img = image_data[y:y+h, x:x+w]
            return await analyze_emotion(face_img)
        return {}
    except Exception as e:
        print(f"Error in image processing: {str(e)}")
        return {}

async def extract_frames(video_path: str, num_frames: int = 10) -> List[np.ndarray]:
    frames = []
    try:
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        interval = max(1, total_frames // num_frames)
        
        for i in range(0, total_frames, interval):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if ret and len(frames) < num_frames:
                frames.append(frame)
        
        cap.release()
    except Exception as e:
        print(f"Error extracting frames: {str(e)}")
    return frames

@router.post("/emotion/analysis")
async def emotion_analysis(
    files: List[UploadFile] = File(...),  # Accept multiple files
    current_user: dict = Depends(get_current_user),
):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            results = []

            for file in files:
                file_path = os.path.join(temp_dir, file.filename)

                # Save uploaded file
                with open(file_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)

                # Check if the file is a video
                if file.filename.lower().endswith(('.mp4', '.avi', '.mov')):
                    frames = await extract_frames(file_path)  # Extract frames from video
                    for frame in frames:
                        emotion_scores = await process_image(frame)  # Analyze each frame
                        if emotion_scores:
                            results.append(emotion_scores)
                else:
                    # Process image files
                    img = cv2.imread(file_path)
                    emotion_scores = await process_image(img)  # Analyze image
                    if emotion_scores:
                        results.append(emotion_scores)

            if not results:
                raise HTTPException(
                    status_code=400,
                    detail="No faces detected in the content or unsupported file format.",
                )

            # Calculate average scores across all results
            avg_scores = {
                emotion: sum(r.get(emotion, 0) for r in results) / len(results)
                for emotion in results[0].keys()
            }

            # Save analysis results to MongoDB
            analysis_collection = DatabaseConnection.get_collection("emotion_analyses")
            analysis_data = {
                "user_id": str(current_user["_id"]),
                "username": current_user["username"],
                "timestamp": datetime.now(),
                "scores": avg_scores,
                "type": "video" if files[0].filename.lower().endswith(('.mp4', '.avi', '.mov')) else "images",
                "filenames": [file.filename for file in files],
            }
            analysis_collection.insert_one(analysis_data)

            return {
                "status": "success",
                "message": "Facial analysis completed",
                "scores": avg_scores,
                "username": current_user["username"],
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
