from fastapi import APIRouter, HTTPException, Request
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
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
        
        # Validate data against the schema
        submission = PersonalityTestSubmission(**test_data)
        
        # Generate the result
        generated_result = generate_result(submission.questions_data)

        # Get collections
        cognitive_results_collection = DatabaseConnection.get_collection('cognitive_test_results')

        # Prepare submission document
        submission_doc = {
            "user_id": ObjectId(current_user['_id']),
            "username": current_user['username'],
            "test_type": "Cognitive Assessment",
            "submitted_at": datetime.utcnow(),
            "questions_data": test_data['questions_data'],  # Raw question data
            "generated_result": generated_result  # Store the result
        }
        
        # Insert submission into the database
        result = cognitive_results_collection.insert_one(submission_doc)
        
        return {
            "message": "Cognitive test submitted successfully",
            "submission_id": str(result.inserted_id),
            "generated_result": generated_result  # Optionally return the result to the user
        }
    
    except Exception as e:
        # Log the full traceback
        print(f"Error in submit_cognitive_test: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )
    
@router.get("/cognitive/status")
async def get_cognitive_test_status(email: str):
    try:
        if not email:
            raise HTTPException(status_code=400, detail="Email parameter is required.")

        # Get user collection
        user_collection = DatabaseConnection.get_collection('users')

        # Search for the user by email
        user = user_collection.find_one({"email": email})
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        user_id = user["_id"]

        # Get cognitive results collection
        cognitive_results_collection = DatabaseConnection.get_collection('cognitive_test_results')

        # Check if the user has completed the cognitive test
        test_result = cognitive_results_collection.find_one({
            "user_id": ObjectId(user_id),
            "test_type": "Cognitive Assessment"
        })

        if not test_result:
            return {
                "has_completed_test": False,
                "completed_at": None,
                "test_data": None
            }

        # Convert ObjectId and other non-serializable fields
        test_result["_id"] = str(test_result["_id"])
        test_result["user_id"] = str(test_result["user_id"])
        completed_at = test_result.get('submitted_at').isoformat() if 'submitted_at' in test_result else None

        return {
            "has_completed_test": True,
            "completed_at": completed_at,
            "test_data": test_result
        }
    except Exception as e:
        print(f"Error fetching test status: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching test status: {str(e)}"
        )

def generate_result(questions_data):
    try:
        # Assuming each question is worth 5 points
        total_score = 0
        total_questions = len(questions_data)
        
        # Define scoring logic based on answer options (you can modify the scale as per your requirements)
        option_to_score = {
            "Never": 1,
            "Rarely": 2,
            "Sometimes": 3,
            "Often": 4,
            "Always": 5
        }

        # Areas of improvement (this can be expanded based on your questions)
        areas_of_improvement = {
            "Motivation": [],
            "Enthusiasm": [],
            "Stress Management": [],
            "Social Connection": [],
            "Emotional Balance": []
        }

        # Test summary data
        summary = []
        
        # Process each question's data
        for question in questions_data:
            # Access the Pydantic model's attributes directly
            question_id = question.question_id
            selected_answer = question.selected_answer
            
            # Get the score for the selected answer
            score = option_to_score.get(selected_answer, 0)  # Default to 0 if not found
            total_score += score
            
            # Here we can map question IDs to specific areas (you can expand this logic)
            if question_id in [1, 2, 5, 6]:
                areas_of_improvement["Motivation"].append(question_id)
            elif question_id in [3, 4, 9, 10]:
                areas_of_improvement["Enthusiasm"].append(question_id)
            elif question_id in [7, 8, 16]:
                areas_of_improvement["Stress Management"].append(question_id)
            elif question_id in [12, 13, 17]:
                areas_of_improvement["Social Connection"].append(question_id)
            elif question_id in [14, 15, 18]:
                areas_of_improvement["Emotional Balance"].append(question_id)
            
            # Collecting detailed information for summary
            summary.append(f"Q{question_id}: Selected answer - {selected_answer} (Score: {score})")
        
        # Calculate percentage score
        percentage_score = (total_score / (total_questions * 5)) * 100
        
        # Generate test summary
        test_summary = "Your overall performance on this cognitive assessment shows strong potential, with notable areas for improvement. "
        if len(areas_of_improvement["Motivation"]) > 0:
            test_summary += "Focus on enhancing your motivation, "
        if len(areas_of_improvement["Enthusiasm"]) > 0:
            test_summary += "boosting your enthusiasm, "
        if len(areas_of_improvement["Stress Management"]) > 0:
            test_summary += "improving your stress management skills, "
        if len(areas_of_improvement["Social Connection"]) > 0:
            test_summary += "strengthening your social connections, "
        if len(areas_of_improvement["Emotional Balance"]) > 0:
            test_summary += "and balancing your emotions more effectively. "
        
        # Trim the trailing comma and space from the summary if needed
        test_summary = test_summary.rstrip(", ")
        
        # Finalize the summary to ensure it reads well
        test_summary += "Keep working on these areas to further enhance your cognitive well-being."

        # Create the result object to return
        result = {
            "total_score": total_score,
            "percentage_score": percentage_score,
            "test_summary": test_summary,
            "areas_of_improvement": [area for area, questions in areas_of_improvement.items() if len(questions) > 0],
            "detailed_scores": [{"question_id": question_id, "selected_option": selected_answer, "score": option_to_score.get(selected_answer, 0)} for question in questions_data]
        }
        
        return result
    
    except Exception as e:
        raise ValueError(f"Failed to generate results: {str(e)}")

# Backend API
@router.get("/cognitive/test-data")
async def get_cognitive_test_data(email: str):
    try:
        if not email:
            raise HTTPException(status_code=400, detail="Email parameter is required.")

        user_collection = DatabaseConnection.get_collection('users')
        cognitive_results_collection = DatabaseConnection.get_collection('cognitive_test_results')

        user = user_collection.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        test_result = cognitive_results_collection.find_one(
            {"user_id": ObjectId(user["_id"])},
            sort=[("submitted_at", -1)]
        )

        if not test_result:
            raise HTTPException(status_code=404, detail="No test data found")

        return {
            "total_score": test_result["generated_result"]["total_score"],
            "percentage_score": test_result["generated_result"]["percentage_score"],
            "test_summary": test_result["generated_result"]["test_summary"],
            "areas_of_improvement": test_result["generated_result"]["areas_of_improvement"],
            "detailed_scores": test_result["generated_result"]["detailed_scores"],
            "questions_data": test_result["questions_data"],
            "submitted_at": test_result["submitted_at"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))