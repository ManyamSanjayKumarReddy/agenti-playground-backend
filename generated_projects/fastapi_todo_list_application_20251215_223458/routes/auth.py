from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db

router = APIRouter()

@router.post("/login")
async def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not db_user.verify_password(user.password):
        return {"error": "Invalid credentials"}
    return {"message": "Login successful", "user_id": db_user.id}

@router.post("/register")
async def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = models.User(email=user.email)
    db_user.set_password(user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User registered successfully", "user_id": db_user.id}
