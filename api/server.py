"""
小伴 FastAPI Web 服务 v1.0
提供 RESTful API 接口，使小伴可作为后端服务部署。

接口列表：
  POST /chat              — 主对话接口（RAG + LLM）
  POST /homework          — 作业辅导（苏格拉底式）
  GET  /diagnosis         — 获取最新学情诊断
  POST /mistake           — 添加错题
  GET  /mistakes          — 查询错题本
  GET  /xiaoshengchu/plan — 获取小升初规划
  GET  /xiaoshengchu/sim  — 志愿填报模拟
  POST /policy/check      — 手动触发政策检查
  GET  /policy/alerts     — 获取最新政策预警
  GET  /health            — 健康检查
  GET  /stats             — 系统统计
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# 将项目根目录加入 Python 路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# ─────────────────────────────────────────────
# 初始化 FastAPI 应用
# ─────────────────────────────────────────────
app = FastAPI(
    title="小伴 API",
    description="北京市海淀区七一小学成长陪伴智能体 — 后端服务",
    version="5.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# 懒加载引擎（避免启动时间过长）
# ─────────────────────────────────────────────
_engines = {}

def get_rag():
    if "rag" not in _engines:
        from engines.rag_engine import RAGEngine
        _engines["rag"] = RAGEngine(str(BASE_DIR))
    return _engines["rag"]

def get_memory():
    if "memory" not in _engines:
        from memory.memory_manager import MemoryManager
        _engines["memory"] = MemoryManager(str(BASE_DIR / "memory"))
    return _engines["memory"]

def get_llm_core():
    if "llm" not in _engines:
        from engines.llm_core import XiaoBanLLMCore
        _engines["llm"] = XiaoBanLLMCore()
    return _engines["llm"]

def get_diagnostics():
    if "diagnostics" not in _engines:
        from engines.academic_diagnostics import AcademicDiagnosticsEngine
        _engines["diagnostics"] = AcademicDiagnosticsEngine(str(BASE_DIR))
    return _engines["diagnostics"]

def get_monitor():
    if "monitor" not in _engines:
        from engines.policy_monitor import PolicyMonitor
        _engines["monitor"] = PolicyMonitor(str(BASE_DIR))
    return _engines["monitor"]

def get_simulator():
    if "simulator" not in _engines:
        from engines.xiaoshengchu_simulator import XiaoshengchuSimulator
        _engines["simulator"] = XiaoshengchuSimulator()
    return _engines["simulator"]

# ─────────────────────────────────────────────
# 请求/响应模型
# ─────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    speaker: str = "parent"  # "parent" | "student"
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    intent: str
    skill_used: str
    latency_ms: float
    sources: list = []

class HomeworkRequest(BaseModel):
    subject: str
    question: str
    student_answer: Optional[str] = None
    grade: str = "六年级"

class MistakeRequest(BaseModel):
    subject: str
    question: str
    student_answer: str
    correct_answer: str
    analysis: Optional[str] = None
    knowledge_point: Optional[str] = None

class PolicyCheckResponse(BaseModel):
    sources_checked: int
    new_articles: int
    elapsed_seconds: float
    articles: list

# ─────────────────────────────────────────────
# 核心接口
# ─────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "5.0.0",
        "agent": "小伴",
        "timestamp": datetime.now().isoformat(),
        "base_dir": str(BASE_DIR)
    }

@app.get("/stats")
async def get_stats():
    """系统统计"""
    memory = get_memory()
    rag = get_rag()
    monitor = get_monitor()
    
    profile = memory.get_profile()
    rag_stats = rag.get_index_stats()
    monitor_status = monitor.get_status()
    
    return {
        "student": profile.get("name", "小可爱"),
        "grade": profile.get("grade", "六年级"),
        "rag_index": rag_stats,
        "policy_monitor": monitor_status,
        "engines_loaded": list(_engines.keys()),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    主对话接口
    自动路由到对应技能模块，RAG 增强回答
    """
    import time
    start = time.time()
    
    try:
        llm_core = get_llm_core()
        memory = get_memory()
        
        # 获取学生上下文
        profile = memory.get_profile()
        student_context = {
            "name": profile.get("name", "小可爱"),
            "grade": profile.get("grade", "六年级"),
            "school_district": "海淀区七一小学",
            "home_address": "丰台东大街5号院"
        }
        
        # 意图识别（返回字符串）
        intent_str = llm_core.detect_intent(request.message)
        
        # RAG 检索增强
        rag = get_rag()
        rag_result = rag.query(request.message, student_context)
        
        # 记录对话历史
        memory.append_dialogue(
            role="user",
            content=request.message,
            speaker=request.speaker,
            skill_used=intent_str
        )
        
        elapsed = (time.time() - start) * 1000
        
        return ChatResponse(
            reply=rag_result["answer"],
            intent=intent_str,
            skill_used="rag_engine",
            latency_ms=round(elapsed, 1),
            sources=rag_result.get("sources", [])
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对话处理失败: {str(e)}")

@app.post("/homework")
async def homework_coach(request: HomeworkRequest):
    """
    作业辅导接口（苏格拉底式）
    不直接给答案，引导学生思考
    """
    try:
        from engines.socratic_tutor_engine import SocraticTutorEngine
        tutor = SocraticTutorEngine(str(BASE_DIR))
        
        result = tutor.generate_socratic_questions(
            subject=request.subject,
            question=request.question,
            student_answer=request.student_answer,
            grade=request.grade
        )
        
        return {
            "subject": request.subject,
            "question": request.question,
            "socratic_hints": result.get("hints", []),
            "knowledge_point": result.get("knowledge_point", ""),
            "encouragement": result.get("encouragement", "加油，你可以的！"),
            "should_give_answer": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"辅导处理失败: {str(e)}")

@app.get("/diagnosis")
async def get_diagnosis(force_refresh: bool = False):
    """获取最新学情诊断报告"""
    try:
        diagnostics = get_diagnostics()
        
        # 检查是否有今日报告
        today_report = BASE_DIR / "memory" / "diagnostics" / f"diagnosis_{datetime.now().strftime('%Y%m%d')}.json"
        
        if not force_refresh and today_report.exists():
            import json
            with open(today_report, "r", encoding="utf-8") as f:
                return json.load(f)
        
        return diagnostics.run_full_diagnosis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"诊断失败: {str(e)}")

@app.post("/mistake")
async def add_mistake(request: MistakeRequest):
    """添加错题到错题本"""
    try:
        memory = get_memory()
        memory.add_mistake({
            "subject": request.subject,
            "question": request.question,
            "student_answer": request.student_answer,
            "correct_answer": request.correct_answer,
            "analysis": request.analysis or "",
            "knowledge_point": request.knowledge_point or "",
            "summary": f"{request.subject}: {request.question[:30]}"
        })
        return {"status": "success", "message": "错题已记录，将按艾宾浩斯曲线安排复习"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录失败: {str(e)}")

@app.get("/mistakes")
async def get_mistakes(subject: Optional[str] = None, limit: int = 20):
    """查询错题本"""
    try:
        import json
        mistake_path = BASE_DIR / "memory" / "mistake_book.json"
        if not mistake_path.exists():
            return {"entries": [], "total": 0}
        
        with open(mistake_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        entries = data.get("entries", [])
        if subject:
            entries = [e for e in entries if e.get("subject") == subject]
        
        return {
            "entries": entries[-limit:],
            "total": len(entries),
            "filtered_by_subject": subject
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/xiaoshengchu/plan")
async def get_xiaoshengchu_plan():
    """获取小升初规划"""
    try:
        from skills.xiaoshengchu_planner import XiaoshengchuPlanner
        planner = XiaoshengchuPlanner(str(BASE_DIR / "memory"))
        analysis = planner.analyze_pathways()
        return {
            "student": "小可爱",
            "school": "七一小学",
            "analysis": analysis,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/xiaoshengchu/sim")
async def simulate_volunteer(strategy: str = "balanced"):
    """
    志愿填报模拟
    strategy: "aggressive" | "balanced" | "conservative"
    """
    try:
        simulator = get_simulator()
        
        if strategy == "aggressive":
            volunteers = ["五十七中", "人大附中翠微学校", "101中学双榆树校区"]
        elif strategy == "conservative":
            volunteers = ["十一实验中学", "育鸿学校", "玉渊潭中学"]
        else:  # balanced
            volunteers = ["五十七中", "十一实验中学", "人大附中翠微学校"]
        
        result = simulator.simulate_strategy(strategy, iterations=500)
        return {
            "strategy": strategy,
            "volunteers": volunteers,
            "simulation_result": result,
            "recommendation": "基于500次模拟的概率分布"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/policy/check", response_model=PolicyCheckResponse)
async def trigger_policy_check(background_tasks: BackgroundTasks):
    """手动触发政策检查（后台执行）"""
    monitor = get_monitor()
    
    # 快速返回，后台执行
    background_tasks.add_task(monitor.check_once)
    
    return PolicyCheckResponse(
        sources_checked=len(monitor.WATCH_TARGETS),
        new_articles=0,
        elapsed_seconds=0,
        articles=[]
    )

@app.get("/policy/alerts")
async def get_policy_alerts(days: int = 7):
    """获取最新政策预警"""
    try:
        monitor = get_monitor()
        alerts = monitor.get_recent_alerts(days=days)
        message = monitor.generate_parent_alert_message()
        
        return {
            "alerts": alerts,
            "total": len(alerts),
            "period_days": days,
            "parent_message": message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────
# 启动入口
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("小伴 FastAPI 服务 v5.0 启动中...")
    print(f"文档地址: http://0.0.0.0:8000/docs")
    print("=" * 60)
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
