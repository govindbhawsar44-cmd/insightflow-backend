from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import prisma
from security import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

class UserCreate(BaseModel):
    email: str
    password: str
    name: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/register", response_model=Token)
async def register(user: UserCreate):
    existing_user = await prisma.user.find_unique(where={"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = await prisma.user.create(
        data={
            "email": user.email,
            "name": user.name,
            "passwordHash": hashed_password
        }
    )
    
    access_token = create_access_token(data={"sub": new_user.id, "email": new_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(user: UserLogin):
    db_user = await prisma.user.find_unique(where={"email": user.email})
    if not db_user or not db_user.passwordHash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(user.password, db_user.passwordHash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": db_user.id, "email": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}
