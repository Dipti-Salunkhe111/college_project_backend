from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from security import decode_token
from db.mongo import DatabaseConnection
from schemas.userSchema import UserCreate, UserLogin, UserInDB
from security import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    decode_token  # Add this import
)
from security import get_password_hash, verify_password, create_access_token
from db.mongo import DatabaseConnection

router = APIRouter()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@router.post("/register")
async def register_user(user: UserCreate):
    # Get users collection
    users_collection = DatabaseConnection.get_collection('users')
    
    # Check if user already exists
    existing_user = users_collection.find_one({"$or": [
        {"email": user.email},
        {"username": user.username}
    ]})
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )
    
    # Create user document
    hashed_password = get_password_hash(user.password)
    user_doc = {
        "username": user.username,
        "email": user.email,
        "hashed_password": hashed_password,
        "full_name": user.full_name
    }
    
    try:
        # Insert user
        result = users_collection.insert_one(user_doc)
        
        # Create access token
        access_token = create_access_token(
            data={"sub": str(result.inserted_id)}
        )
        
        return {
            "message": "User registered successfully",
            "access_token": access_token,
            "token_type": "bearer"
        }
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed"
        )

@router.post("/login")
async def login_user(user: UserLogin):
    # Get users collection
    users_collection = DatabaseConnection.get_collection('users')
    
    # Find user by email
    db_user = users_collection.find_one({"email": user.email})
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(user.password, db_user['hashed_password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(db_user['_id'])}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# Dependency to get current user
async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Decode the token
    payload = decode_token(token)
    
    # Get users collection
    users_collection = DatabaseConnection.get_collection('users')
    
    try:
        # Convert the user ID from string to ObjectId
        user_id = ObjectId(payload.get("sub"))
        
        # Find user by ObjectId
        user = users_collection.find_one({"_id": user_id})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Convert ObjectId to string for JSON serialization
        user['_id'] = str(user['_id'])
        
        return user
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    return user