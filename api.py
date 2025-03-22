from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import cognitive, users, emotions
from db.mongo import db_connection 

app = FastAPI()

# Allow requests from your frontend
origins = [
    "http://localhost:5173",  # Local development (Vite)
    "https://college-project-frontend-three.vercel.app"  # Updated Vercel frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Include route modules
app.include_router(cognitive.router, prefix="/api", tags=["Cognitive"])
app.include_router(emotions.router, prefix="/api", tags=["Emotion"])
app.include_router(users.router, prefix="/api/users", tags=["Authorization"])

# Database connection
@app.on_event("startup")
async def startup_db_client():
    await db_connection.connect()

@app.on_event("shutdown")
async def shutdown_db_client():
    await db_connection.disconnect()

# Health check endpoint
@app.get("/test")
async def test_server():
    return {"message": "Server is running!"}
