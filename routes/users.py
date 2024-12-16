from fastapi import APIRouter

router = APIRouter()

# create a register user API

# create login user API
@router.post("/login")
async def login(data: dict):
    # Process the cognitive test data
    return {"message": "Cognitive test submitted successfully"}
