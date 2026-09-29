from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
import secrets
import uuid

from database import fetch_one, execute_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

def get_signing_key():
    if SECRET_KEY:
        return SECRET_KEY
    setting = fetch_one("SELECT value FROM app_settings WHERE key = ?", ("jwt_secret_key",))
    if setting:
        return setting["value"]
    generated_key = secrets.token_urlsafe(48)
    execute_db(
        "INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)",
        ("jwt_secret_key", generated_key)
    )
    return fetch_one("SELECT value FROM app_settings WHERE key = ?", ("jwt_secret_key",))["value"]

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
    role: str
    created_at: str

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_signing_key(), algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, get_signing_key(), algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if user is None or payload.get("auth_version", 0) != user.get("auth_version", 0):
        raise credentials_exception
    return user


def is_admin_account(user: dict) -> bool:
    configured_admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    return user.get("role") == "admin" or bool(
        configured_admin_email and user.get("email", "").strip().lower() == configured_admin_email
    )


def require_admin(current_user: dict = Depends(get_current_user)):
    if not is_admin_account(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user

def bootstrap_admin():
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not email and not password:
        return
    if not email or len(password) < 12:
        raise RuntimeError("Set both ADMIN_EMAIL and an ADMIN_PASSWORD of at least 12 characters")

    existing = fetch_one("SELECT id, role FROM users WHERE lower(email) = lower(?)", (email,))
    if existing:
        if existing["role"] != "admin":
            execute_db(
                "UPDATE users SET role = 'admin', password_hash = ?, auth_version = auth_version + 1 WHERE id = ?",
                (pwd_context.hash(password), existing["id"])
            )
        return

    execute_db(
        "INSERT INTO users (id, name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, 'admin', ?)",
        (str(uuid.uuid4()), "BroChat Admin", email, pwd_context.hash(password), datetime.utcnow().isoformat())
    )

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
    
    access_token = create_access_token(data={"sub": user_id, "auth_version": 0})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
def login(user: UserLogin):
    db_user = fetch_one("SELECT * FROM users WHERE email = ?", (user.email,))
    if not db_user or not pwd_context.verify(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
        
    access_token = create_access_token(data={"sub": db_user["id"], "auth_version": db_user.get("auth_version", 0)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
def read_users_me(current_user: dict = Depends(get_current_user)):
    response = dict(current_user)
    if is_admin_account(response):
        response["role"] = "admin"
    return response
