"""
API Server for RecBole Project using FastAPI.

This server provides endpoints:
- POST /user_action            : receive one user behavior event and append to user_actions.log
- POST /user_actions_batch     : receive a list of events and append
- GET  /recommendations/{user} : get recommendations for a user (real inference)
- GET  /health                 : health check
- GET  /schema                 : contract for web team

Auth: Expect header Authorization: Bearer <API_KEY> if API_KEY is set.
CORS: Allowed for all origins by default (tune for production).
"""
import json
import os
from typing import List, Optional, Union

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
import uvicorn

# Import inference module
from inference import get_recommendations as inference_get_recommendations, load_model, clear_cache

# -----------------------------
# Configs
# -----------------------------
LOG_FILE = os.getenv("USER_ACTION_LOG_FILE", "data/user_actions.log")
API_KEY = os.getenv("API_KEY", "")  # set to a non-empty string in production
_allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "*")
if not _allowed_origins_raw or _allowed_origins_raw.strip() == "*" or _allowed_origins_raw.strip() == "":
    CORS_ALLOW_ORIGINS = ["*"]
    CORS_ALLOW_CREDENTIALS = False
else:
    CORS_ALLOW_ORIGINS = [origin.strip() for origin in _allowed_origins_raw.split(",") if origin.strip()]
    CORS_ALLOW_CREDENTIALS = True
ALLOWED_ACTIONS = {"click", "like", "share", "booking"}

# -----------------------------
# Pydantic models
# -----------------------------
class UserAction(BaseModel):
    user_id: Union[str, int]  # Chấp nhận cả string và int
    item_id: Union[str, int]  # Chấp nhận cả string và int
    action_type: str  # 'click' | 'like' | 'share' | 'booking'
    timestamp: float

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_user_id(cls, v) -> str:
        # Convert int → str để xử lý thống nhất
        v = str(v).strip()
        if not v:
            raise ValueError("user_id cannot be empty")
        if len(v) > 100:
            raise ValueError(f"user_id too long (max 100 characters), got {len(v)}")
        return v
    
    @field_validator("item_id", mode="before")
    @classmethod
    def validate_item_id(cls, v) -> str:
        # Convert int → str để xử lý thống nhất
        v = str(v).strip()
        if not v:
            raise ValueError("item_id cannot be empty")
        if len(v) > 100:
            raise ValueError(f"item_id too long (max 100 characters), got {len(v)}")
        return v

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ALLOWED_ACTIONS:
            raise ValueError(f"action_type must be one of {sorted(ALLOWED_ACTIONS)}, got '{v}'")
        return v
    
    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"timestamp must be >= 0, got {v}")
        # Check reasonable range (từ 2000-01-01 đến 2100-01-01)
        if v < 946684800 or v > 4102444800:
            raise ValueError(f"timestamp out of reasonable range (2000-01-01 to 2100-01-01), got {v}")
        return v

# -----------------------------
# Helpers
# -----------------------------
def _append_log_line(payload: dict) -> None:
    """Append một dòng JSON vào log file với error handling.
    
    Convert user_id và item_id về int nếu có thể để giữ nguyên format từ web.
    JSON serialize int sẽ giữ nguyên int (không phải float).
    """
    try:
        # Convert user_id và item_id về int nếu có thể (để giữ nguyên format từ web)
        # JSON serialize int sẽ giữ nguyên int, không phải float
        log_payload = payload.copy()
        try:
            if 'user_id' in log_payload and isinstance(log_payload['user_id'], str):
                # Chỉ convert nếu là string (từ Pydantic validator)
                log_payload['user_id'] = int(log_payload['user_id'])
        except (ValueError, TypeError):
            pass  # Giữ nguyên nếu không convert được
        
        try:
            if 'item_id' in log_payload and isinstance(log_payload['item_id'], str):
                # Chỉ convert nếu là string (từ Pydantic validator)
                log_payload['item_id'] = int(log_payload['item_id'])
        except (ValueError, TypeError):
            pass  # Giữ nguyên nếu không convert được
        
        os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_payload, ensure_ascii=False) + "\n")
    except IOError as e:
        # Log error nhưng không crash server
        print(f"[API] ERROR: Không thể ghi vào log file {LOG_FILE}: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable: cannot write to log file"
        )
    except Exception as e:
        print(f"[API] ERROR: Lỗi không mong đợi khi ghi log: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while logging action"
        )

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

# CORS - configurable via environment variable (default: allow all, no credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the RecBole Recommendation API!"}

@app.get("/health")
def health():
    """Health check endpoint - kiểm tra model đã load chưa."""
    try:
        # Kiểm tra model đã load chưa
        from inference import is_model_loaded
        model_loaded = is_model_loaded()
        return {
            "ok": True,
            "model_loaded": model_loaded
        }
    except:
        return {"ok": True, "model_loaded": False}

@app.get("/metrics")
def metrics():
    """Metrics endpoint - trả về thống kê API usage."""
    try:
        from monitoring import get_metrics
        return get_metrics()
    except ImportError:
        return {"error": "Monitoring not available"}

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
    """Nhận một hành vi người dùng và lưu vào log file.
    
    Returns:
        Dict với status và data nếu thành công
    """
    try:
        _require_api_key(authorization)
        payload = action.model_dump()
        _append_log_line(payload)
        return {"status": "success", "data": payload}
    except HTTPException:
        # Re-raise HTTPException
        raise
    except ValueError as e:
        # Validation error từ Pydantic
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except Exception as e:
        print(f"[API] ERROR trong log_user_action: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/user_actions_batch")
def log_user_actions_batch(actions: List[UserAction], authorization: Optional[str] = Header(default=None)):
    _require_api_key(authorization)
    # append each action on a single line for ETL simplicity
    for a in actions:
        _append_log_line(a.model_dump())
    return {"status": "success", "count": len(actions)}

@app.on_event("startup")
def startup_event():
    """Load model khi server start (cache model để tránh load lại mỗi request)."""
    try:
        print("[API] Đang load model khi khởi động server...")
        load_model()
        print("[API] Model đã được load thành công!")
    except Exception as e:
        print(f"[API] WARNING: Không thể load model khi khởi động: {e}")
        print("[API] Model sẽ được load khi có request đầu tiên.")


@app.get("/recommendations/{user_id}")
def get_recommendations(
    user_id: str,
    top_k: int = 10,
    use_behavior_boost: bool = True,
    use_similarity_boost: bool = True,  # NEW: Phase 2
    alpha: float = 0.3,
    decay_rate: float = 0.1,
    behavior_hours: int = 24,
    similarity_threshold: float = 0.5,  # NEW: Phase 2
    similarity_boost_factor: float = 0.5,  # NEW: Phase 2
    authorization: Optional[str] = Header(default=None)
):
    """Lấy recommendations cho user từ model đã train.
    
    NEW (Phase 1): Hỗ trợ behavior boost từ user_actions.log để recommendations real-time và personalized.
    NEW (Phase 2): Hỗ trợ similarity boost - boost hotels tương tự hotels đã tương tác.
    
    Args:
        user_id: ID của user (external token)
        top_k: Số lượng recommendations cần trả về (mặc định: 10, tối đa: 100)
        use_behavior_boost: Nếu True, áp dụng behavior boost từ user_actions.log (default: True, Phase 1)
        use_similarity_boost: Nếu True, áp dụng similarity boost (default: True, Phase 2) - chỉ hoạt động nếu use_behavior_boost=True
        alpha: Boost coefficient (0.3 = tối đa 30% boost, default: 0.3)
        decay_rate: Time decay rate (0.1 = giảm ~10% mỗi giờ, default: 0.1)
        behavior_hours: Số giờ gần đây cần lấy actions (default: 24)
        similarity_threshold: Chỉ boost items có similarity >= threshold (default: 0.5, Phase 2)
        similarity_boost_factor: Trọng số cho similarity boost (0.5 = boost 50% của direct boost, default: 0.5, Phase 2)
        
    Returns:
        Dict với user_id, recommendations (list of item IDs), và model_version
    """
    # Auth (nếu bật)
    _require_api_key(authorization)

    # Validate user_id
    user_id = user_id.strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id cannot be empty")
    if len(user_id) > 100:
        raise HTTPException(status_code=400, detail=f"user_id too long (max 100 characters)")
    
    # Validate top_k
    if top_k < 1:
        raise HTTPException(status_code=400, detail="top_k must be >= 1")
    if top_k > 100:
        raise HTTPException(status_code=400, detail="top_k must be <= 100")
    
    try:
        # Kiểm tra model đã load chưa
        from inference import is_model_loaded, load_model
        if not is_model_loaded():
            print("[API] Model chưa load, đang load model...")
            try:
                load_model()
            except Exception as e:
                raise HTTPException(
                    status_code=503,
                    detail=f"Model không thể load được: {str(e)}"
                )
        
        # Validate behavior boost parameters
        if alpha < 0 or alpha > 1:
            raise HTTPException(status_code=400, detail="alpha must be between 0 and 1")
        if decay_rate < 0 or decay_rate > 1:
            raise HTTPException(status_code=400, detail="decay_rate must be between 0 and 1")
        if behavior_hours < 1 or behavior_hours > 168:  # 1 hour to 7 days
            raise HTTPException(status_code=400, detail="behavior_hours must be between 1 and 168")
        
        # Validate similarity boost parameters (Phase 2)
        if similarity_threshold < 0 or similarity_threshold > 1:
            raise HTTPException(status_code=400, detail="similarity_threshold must be between 0 and 1")
        if similarity_boost_factor < 0 or similarity_boost_factor > 2:
            raise HTTPException(status_code=400, detail="similarity_boost_factor must be between 0 and 2")
        
        # Lấy recommendations từ inference module
        recommendations = inference_get_recommendations(
            user_id=user_id,
            top_k=top_k,
            exclude_interacted=True,
            use_behavior_boost=use_behavior_boost,
            use_similarity_boost=use_similarity_boost,
            alpha=alpha,
            decay_rate=decay_rate,
            behavior_hours=behavior_hours,
            similarity_threshold=similarity_threshold,
            similarity_boost_factor=similarity_boost_factor
        )
        
        # Lấy model version (tên file checkpoint mới nhất)
        import glob
        checkpoints = glob.glob("saved/DeepFM-*.pth")
        if checkpoints:
            latest_checkpoint = max(checkpoints, key=os.path.getmtime)
            model_version = os.path.basename(latest_checkpoint).replace(".pth", "")
        else:
            model_version = "unknown"
        
        return {
            "user_id": user_id,
            "recommendations": recommendations,
            "model_version": model_version,
            "top_k": len(recommendations)
        }
        
    except ValueError as e:
        # User không tồn tại trong dataset (cold start)
        # Trả về empty list - backend team sẽ xử lý cold start
        import glob
        checkpoints = glob.glob("saved/DeepFM-*.pth")
        if checkpoints:
            latest_checkpoint = max(checkpoints, key=os.path.getmtime)
            model_version = os.path.basename(latest_checkpoint).replace(".pth", "")
        else:
            model_version = "unknown"
        
        return {
            "user_id": user_id,
            "recommendations": [],
            "model_version": model_version,
            "top_k": 0,
            "message": "User mới (cold start) - không có dữ liệu trong dataset. Backend sẽ xử lý gợi ý theo IP location."
        }
    except HTTPException:
        # Re-raise HTTPException
        raise
    except FileNotFoundError as e:
        # Model file không tồn tại
        raise HTTPException(
            status_code=503,
            detail="Model không tìm thấy. Vui lòng liên hệ admin."
        )
    except Exception as e:
        # Lỗi khác
        import traceback
        error_detail = str(e)
        print(f"[API] ERROR trong get_recommendations: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy recommendations: {error_detail}"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
