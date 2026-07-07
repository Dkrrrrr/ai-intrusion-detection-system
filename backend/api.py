# backend/api.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from ids_core import IDSCore

app = FastAPI(title="IDS Intelligence API", description="入侵检测与 AI Agent 响应接口")
core = IDSCore()

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求/响应模型
class PredictRequest(BaseModel):
    features: List[float]

class PredictResponse(BaseModel):
    prediction: str
    probability: Dict[str, float]

class AgentDecideRequest(BaseModel):
    attack_type: str
    src_ip: str
    risk_level: str = "高"

class AgentDecideResponse(BaseModel):
    action: str
    full_response: str

class AgentExplainRequest(BaseModel):
    attack_type: str
    features: Dict[str, float]

class AgentExplainResponse(BaseModel):
    explanation: str

class StatsResponse(BaseModel):
    total_predictions: int
    total_attacks_detected: int
    recent_decisions: List[Dict]

# API 端点
@app.get("/")
def root():
    return {"message": "IDS API is running", "model_loaded": core.model is not None}

@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    try:
        result = core.predict(req.features)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/decide", response_model=AgentDecideResponse)
async def agent_decide(req: AgentDecideRequest):
    try:
        result = core.agent_decide(req.attack_type, req.src_ip, req.risk_level)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/explain", response_model=AgentExplainResponse)
async def agent_explain(req: AgentExplainRequest):
    try:
        explanation = core.agent_explain(req.attack_type, req.features)
        return AgentExplainResponse(explanation=explanation)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats", response_model=StatsResponse)
async def stats():
    return core.get_stats()

# ============================================================
# RAG 知识库统计接口
# ============================================================

@app.get("/rag/stats")
async def rag_stats():
    """
    获取 RAG 知识库的统计信息
    """
    try:
        from agent_core import get_rag_stats
        stats = get_rag_stats()
        return {
            "status": "ok",
            "stats": stats
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }