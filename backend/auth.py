from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import uuid

from database import fetch_one, execute_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

SECRET_KEY = "brochat-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserOut(BaseModel):
    id: str
    name: str
    email: str
    created_at: str

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if user is None:
        raise credentials_exception
    return user

@router.post("/signup", response_model=Token)
def signup(user: UserCreate):
    existing = fetch_one("SELECT * FROM users WHERE email = ?", (user.email,))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    user_id = str(uuid.uuid4())
    hashed_password = pwd_context.hash(user.password)
    
    execute_db(
        "INSERT INTO users (id, name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, user.name, user.email, hashed_password, datetime.utcnow().isoformat())
    )
    
    access_token = create_access_token(data={"sub": user_id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
def login(user: UserLogin):
    db_user = fetch_one("SELECT * FROM users WHERE email = ?", (user.email,))
    if not db_user or not pwd_context.verify(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
        
    access_token = create_access_token(data={"sub": db_user["id"]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
