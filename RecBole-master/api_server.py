"""
API Server for RecBole Project using FastAPI.

This server provides endpoints:
- POST /user_action            : receive one user behavior event and append to user_actions.log
- POST /user_actions_batch     : receive a list of events and append
- GET  /recommendations/{user} : placeholder for inference
- GET  /health                 : health check
- GET  /schema                 : contract for web team

Auth: Expect header Authorization: Bearer <API_KEY> if API_KEY is set.
CORS: Allowed for all origins by default (tune for production).
"""
import json
import os
from typing import List, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
import uvicorn

# -----------------------------
# Configs
# -----------------------------
LOG_FILE = os.getenv("USER_ACTION_LOG_FILE", "user_actions.log")
API_KEY = os.getenv("API_KEY", "")  # set to a non-empty string in production
ALLOWED_ACTIONS = {"click", "like", "share", "booking"}

# -----------------------------
# Pydantic models
# -----------------------------
class UserAction(BaseModel):
    user_id: str
    item_id: str
    action_type: str  # 'click' | 'like' | 'share' | 'booking'
    timestamp: float

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        if v not in ALLOWED_ACTIONS:
            raise ValueError(f"action_type must be one of {sorted(ALLOWED_ACTIONS)}")
        return v

# -----------------------------
# Helpers
# -----------------------------
def _append_log_line(payload: dict) -> None:
    os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

def _require_api_key(authorization: Optional[str]) -> None:
    if not API_KEY:
        return  # auth disabled
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1].strip()
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

# -----------------------------
# FastAPI app
# -----------------------------
app = FastAPI(title="RecBole Recommendation API", version="1.0.0")

# CORS - allow all by default (customize in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the RecBole Recommendation API!"}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/schema")
def schema():
    return {
        "endpoint": "/user_action",
        "method": "POST",
        "headers": {"Authorization": "Bearer <API_KEY>", "Content-Type": "application/json"},
        "body": {
            "user_id": "string",
            "item_id": "string",
            "action_type": sorted(list(ALLOWED_ACTIONS)),
            "timestamp": "unix_seconds(float)"
        }
    }

@app.post("/user_action")
def log_user_action(action: UserAction, authorization: Optional[str] = Header(default=None)):
    _require_api_key(authorization)
    payload = action.model_dump()
    _append_log_line(payload)
    return {"status": "success", "data": payload}

@app.post("/user_actions_batch")
def log_user_actions_batch(actions: List[UserAction], authorization: Optional[str] = Header(default=None)):
    _require_api_key(authorization)
    # append each action on a single line for ETL simplicity
    for a in actions:
        _append_log_line(a.model_dump())
    return {"status": "success", "count": len(actions)}

@app.get("/recommendations/{user_id}")
def get_recommendations(user_id: str, top_k: int = 10):
    # Placeholder inference
    recs = [f"hotel_{i}" for i in range(100, 100 + top_k)]
    return {"user_id": user_id, "recommendations": recs, "model_version": "0.1.0-simulated"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
