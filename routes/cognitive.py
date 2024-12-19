from fastapi import APIRouter, HTTPException, Request
from bson import ObjectId
from datetime import datetime
from db.mongo import DatabaseConnection
from schemas.testSchema import TestDataSchema, PersonalityTestSubmission
from routes.users import get_current_user
import traceback

router = APIRouter()

# create a /cognitive as base address

# create an get questions API from mongoDB
from fastapi import APIRouter, HTTPException
from db.mongo import DatabaseConnection
from schemas.testSchema import TestDataSchema
from schemas.testSchema import PersonalityTestSubmission

router = APIRouter()

from fastapi import APIRouter, HTTPException, Depends
from db.mongo import DatabaseConnection
from schemas.testSchema import TestDataSchema
from routes.cognitive import get_current_user  # Import the existing authentication dependency

router = APIRouter()

@router.get("/cognitive/questions", response_model=TestDataSchema)
async def get_test_questions(
    test_type: str = "Cognitive Assessment", 
    current_user: dict = Depends(get_current_user)  # Add authentication dependency
):
    # Get test_data collection
    test_data_collection = DatabaseConnection.get_collection('test_data')
    
    # Find the document by test type
    test_data = test_data_collection.find_one({"test_type": test_type})
    
    if not test_data:
        raise HTTPException(
            status_code=404, 
            detail=f"No test data found for test type: {test_type}"
        )
    
    # Remove MongoDB's internal _id 
    test_data.pop('_id', None)
    
    return test_data

@router.post("/cognitive/submit")
async def submit_cognitive_test(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    try:
        # Parse request body
        test_data = await request.json()
        
        # Validate input
        if not test_data or 'questions_data' not in test_data:
            raise HTTPException(
                status_code=400, 
                detail="Invalid request body"
            )
        
        # Get collections
        cognitive_results_collection = DatabaseConnection.get_collection('cognitive_test_results')
        
        # Prepare submission document
        submission_doc = {
            "user_id": ObjectId(current_user['_id']),
            "username": current_user['username'],
            "test_type": "Cognitive Assessment",
            "submitted_at": datetime.utcnow(),
            "questions_data": test_data['questions_data']
        }
        
        # Insert submission
        result = cognitive_results_collection.insert_one(submission_doc)
        
        return {
            "message": "Cognitive test submitted successfully",
            "submission_id": str(result.inserted_id)
        }
    
    except Exception as e:
        # Log the full traceback
        print(f"Error in submit_cognitive_test: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )
    
@router.get("/cognitive/status")
async def get_cognitive_test_status(
    current_user: dict = Depends(get_current_user)
):
    # Get cognitive results collection
    cognitive_results_collection = DatabaseConnection.get_collection('cognitive_test_results')
    
    # Check if the user has completed the cognitive test
    test_result = cognitive_results_collection.find_one({
        "user_id": ObjectId(current_user['_id']),
        "test_type": "Cognitive Assessment"
    })
    
    # Return status
    return {
        "has_completed_test": test_result is not None,
        "completed_at": test_result['submitted_at'] if test_result else None
    }