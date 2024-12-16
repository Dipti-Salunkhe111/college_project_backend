from fastapi import APIRouter

router = APIRouter()

# create a /cognitive as base address

# create an get questions API from mongoDB


@router.post("/cognitive/submit")
async def submit_cognitive_test(data: dict):
    # 1) save the question and answer data of user in MongoDB in their colletion
    return {"message": "Cognitive test submitted successfully"}
