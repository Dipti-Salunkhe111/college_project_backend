from fastapi import APIRouter

router = APIRouter()

# create a /cognitive as base address

# create an get questions API from mongoDB


@router.post("/emotion/analysis")
async def emotion_analysis(data: dict):
    # 1) check if the file type is video of folder
    # 2) if it is a video then call the emotion detection function using video
    # 3) if it is a folder then extract all the images from the images and then call the emotion detection function using images
    return {"message": "Cognitive test submitted successfully"}
