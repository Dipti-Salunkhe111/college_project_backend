from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from db.mongo import DatabaseConnection
from routes.users import get_current_user
import cv2
import numpy as np
from datetime import datetime
import tempfile
import os
from typing import List
from tensorflow.keras.models import model_from_json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Global variables for the model and cascade
emotion_model = None
face_cascade = None

# Emotion labels
emotion_dict = {0: "Angry", 1: "Disgusted", 2: "Fearful", 3: "Happy", 4: "Neutral", 5: "Sad", 6: "Surprised"}

def load_model():
    """Load the pre-trained emotion model and Haar Cascade classifier."""
    global emotion_model, face_cascade
    try:
        # Load model architecture from JSON file
        with open('services/emotion_model.json', 'r') as json_file:
            model_json = json_file.read()
        emotion_model = model_from_json(model_json)
        # Load model weights
        emotion_model.load_weights("services/emotion_model.weights.h5")
        logger.info("Emotion model loaded successfully")
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
    except Exception as e:
        logger.error(f"Error loading emotion model: {str(e)}")

    try:
        # Load Haar Cascade for face detection
        face_cascade = cv2.CascadeClassifier('services/haarcascade_frontalface_default.xml')
        if face_cascade.empty():
            raise ValueError("Haar Cascade classifier is empty or invalid")
        logger.info("Haar Cascade classifier loaded successfully")
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
    except Exception as e:
        logger.error(f"Error loading Haar Cascade: {str(e)}")

# Load the model when the module is imported
load_model()

def preprocess_face(face_img):
    """Preprocess the face image for the emotion model."""
    try:
        # Ensure the image is grayscale
        if len(face_img.shape) == 3:
            gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_img
        # Resize to 48x48 pixels
        resized = cv2.resize(gray, (48, 48))
        # Normalize pixel values to [0, 1]
        normalized = resized / 255.0
        # Add batch and channel dimensions
        preprocessed = np.expand_dims(np.expand_dims(normalized, -1), 0)
        return preprocessed
    except Exception as e:
        logger.error(f"Error preprocessing face: {str(e)}")
        return None

async def process_image(image_data):
    """Process the image to detect faces and predict emotions using the model."""
    try:
        gray = cv2.cvtColor(image_data, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        logger.info(f"Detected {len(faces)} faces in the image")
        
        if len(faces) == 0:
            logger.warning("No faces detected in the image")
            return {}
        
        predictions = []
        for (x, y, w, h) in faces:
            face = gray[y:y+h, x:x+w]
            preprocessed = preprocess_face(face)
            if preprocessed is not None:
                prediction = emotion_model.predict(preprocessed)[0]
                dominant_emotion_idx = np.argmax(prediction)
                dominant_emotion = emotion_dict[dominant_emotion_idx]
                confidence = float(prediction[dominant_emotion_idx])
                logger.info(f"Face at ({x}, {y}, {w}, {h}): Predicted {dominant_emotion} with confidence {confidence:.4f}")
                predictions.append(prediction)
        
        if predictions:
            avg_prediction = np.mean(predictions, axis=0)
            emotion_scores = {emotion_dict[i]: float(avg_prediction[i]) for i in range(7)}
            dominant_emotion = max(emotion_scores, key=emotion_scores.get)
            logger.info(f"Average emotion scores for image: {emotion_scores}")
            logger.info(f"Dominant emotion for image: {dominant_emotion} with probability {emotion_scores[dominant_emotion]:.4f}")
            return emotion_scores
        else:
            return {}
    except Exception as e:
        logger.error(f"Error in image processing: {str(e)}")
        return {}

async def extract_frames(video_path, num_frames=10):
    """Extract frames from a video for emotion analysis."""
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
        logger.info(f"Extracted {len(frames)} frames from video: {video_path}")
    except Exception as e:
        logger.error(f"Error extracting frames from {video_path}: {str(e)}")
    return frames

@router.post("/emotion/analysis")
async def emotion_analysis(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Analyze emotions from uploaded images or videos."""
    if emotion_model is None or face_cascade is None:
        logger.error("Model or cascade not loaded")
        raise HTTPException(status_code=500, detail="Model or cascade not loaded")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            all_scores = []
            for file in files:
                file_path = os.path.join(temp_dir, file.filename)
                with open(file_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                
                logger.info(f"Processing file: {file.filename}")
                if file.filename.lower().endswith(('.mp4', '.avi', '.mov')):
                    frames = await extract_frames(file_path)
                    for i, frame in enumerate(frames):
                        logger.info(f"Analyzing frame {i+1}/{len(frames)} from {file.filename}")
                        scores = await process_image(frame)
                        if scores:
                            all_scores.append(scores)
                else:
                    img = cv2.imread(file_path)
                    scores = await process_image(img)
                    if scores:
                        all_scores.append(scores)
            
            if not all_scores:
                logger.warning("No valid emotion scores obtained from the uploaded files")
                raise HTTPException(
                    status_code=400,
                    detail="No faces detected in the content or unsupported file format.",
                )
            
            # Average the scores across all detections
            emotions = all_scores[0].keys()
            avg_scores = {emotion: np.mean([s[emotion] for s in all_scores]) for emotion in emotions}
            
            # Log final results
            dominant_emotion = max(avg_scores, key=avg_scores.get)
            logger.info(f"Final averaged emotion scores: {avg_scores}")
            logger.info(f"Overall dominant emotion: {dominant_emotion} with probability {avg_scores[dominant_emotion]:.4f}")
            
            # Save to database
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
            logger.info(f"Emotion analysis saved to database for user: {current_user['username']}")
            
            return {
                "status": "success",
                "message": "Facial analysis completed",
                "scores": avg_scores,
                "username": current_user["username"],
            }
    except Exception as e:
        logger.error(f"Error in emotion analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/emotion/status")
async def get_emotion_status(current_user: dict = Depends(get_current_user)):
    """Retrieve all emotion analysis data for the current user."""
    try:
        analysis_collection = DatabaseConnection.get_collection("emotion_analyses")
        emotion_data = list(analysis_collection.find({"user_id": str(current_user["_id"])}))
        
        if not emotion_data:
            raise HTTPException(status_code=404, detail="No emotion analyses found for the user")

        for data in emotion_data:
            data["_id"] = str(data["_id"])

        logger.info(f"Fetched {len(emotion_data)} emotion analysis records for user: {current_user['username']}")
        return {
            "status": "success",
            "message": "Emotion analysis data fetched successfully",
            "data": emotion_data,
        }
    except Exception as e:
        logger.error(f"Error fetching emotion status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching emotion status: {str(e)}")

@router.get("/emotion/test-data")
async def get_emotion_test_data(email: str):
    """Retrieve the latest emotion analysis data for a user by email."""
    try:
        if not email:
            raise HTTPException(status_code=400, detail="Email parameter is required.")

        user_collection = DatabaseConnection.get_collection('users')
        emotion_collection = DatabaseConnection.get_collection('emotion_analyses')

        user = user_collection.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        emotion_data = emotion_collection.find_one(
            {"user_id": str(user["_id"])},
            sort=[("timestamp", -1)]
        )

        if not emotion_data:
            raise HTTPException(status_code=404, detail="No emotion data found")

        logger.info(f"Fetched latest emotion data for email: {email}")
        return {
            "scores": emotion_data["scores"],
            "type": emotion_data["type"],
            "filenames": emotion_data["filenames"],
            "timestamp": emotion_data["timestamp"]
        }
    except Exception as e:
        logger.error(f"Error fetching emotion test data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))