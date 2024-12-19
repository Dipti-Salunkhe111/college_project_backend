import os
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.getenv('JWT_SECRET_KEY')
if not SECRET_KEY:
    # Fallback to a default key if not set, but warn about security
    import warnings
    warnings.warn("JWT_SECRET_KEY not set. Using a default key is insecure!")
    SECRET_KEY = "your-secret-key-change-in-production"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    
    # Ensure the secret key is converted to bytes
    if not isinstance(SECRET_KEY, (bytes, str)):
        raise ValueError("SECRET_KEY must be a string or bytes")
    
    # Convert to bytes if it's a string
    secret = SECRET_KEY.encode('utf-8') if isinstance(SECRET_KEY, str) else SECRET_KEY
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    
    # Encode the token
    encoded_jwt = jwt.encode(to_encode, secret, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    try:
        # Ensure the secret key is in bytes
        secret = SECRET_KEY.encode('utf-8') if isinstance(SECRET_KEY, str) else SECRET_KEY
        
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        return payload
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )