import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.events.bus import (
    Event,
    EventCreate,
    get_events,
    get_events_by_agent,
    publish_event,
)
from app.kernel.registry import (
    register_agent,
    get_agents,
)
from app.db import init_db
from app.memory.engine import (
    Memory,
    MemoryCreate,
    get_memories,
    get_memories_by_agent,
    save_memory,
    search_memories,
)
from app.agents.ceo import DailyBrief, generate_daily_brief
from app.agents.cto import CTOBrief, generate_cto_brief
from app.agents.pm import PMBrief, generate_pm_brief
from app.agents.execution_router import router as execution_router
from app.agents.scheduler import start_scheduler, stop_scheduler
from app.knowledge.router import router as knowledge_router
from app.knowledge.importer import start_knowledge_watcher, stop_knowledge_watcher
from app.system.router import router as system_router
from app.projects.router import router as projects_router
from app.collaboration.router import router as collaboration_router
from app.reasoning.router import router as reasoning_router
from app.jira.router import router as jira_router
from app.business.router import router as business_router
from app.communications.router import router as communications_router
from app.whatsapp.router import router as whatsapp_router
from app.demo.router import router as demo_router
from app.demo.service import ensure_demo_data
from app.commercial.router import router as commercial_router
from app.sales.router import router as sales_router
from app.marketing.router import router as marketing_router
from app.copilot.router import router as copilot_router
from app.auth.router import router as auth_router
from app.auth.service import ensure_admin_user
from app.chief_of_staff.router import router as chief_router
from app.capabilities.router import router as capabilities_router
from app.capabilities.service import ensure_default_capabilities
from app.conversations.router import router as conversations_router
from app.planning.router import router as planning_router
from app.runtime.router import router as runtime_router
from app.software_factory.router import router as software_factory_router
from app.enterprise.router import router as enterprise_router
from app.enterprise.schemas import AuditEventCreate
from app.enterprise.service import ensure_enterprise_defaults, record_audit
from app.settings import PardhaMode, get_settings

app = FastAPI(title="Pardha Kernel")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5174", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(business_router)
app.include_router(auth_router)
app.include_router(knowledge_router)
app.include_router(execution_router)
app.include_router(system_router)
app.include_router(projects_router)
app.include_router(collaboration_router)
app.include_router(reasoning_router)
app.include_router(jira_router)
app.include_router(communications_router)
app.include_router(whatsapp_router)
app.include_router(copilot_router)
app.include_router(demo_router)
app.include_router(commercial_router)
app.include_router(sales_router)
app.include_router(marketing_router)
app.include_router(chief_router)
app.include_router(capabilities_router)
app.include_router(conversations_router)
app.include_router(planning_router)
app.include_router(runtime_router)
app.include_router(software_factory_router)
app.include_router(enterprise_router)

_RATE_LIMIT_WINDOW_SECONDS = 60
_RATE_LIMIT_MAX_REQUESTS = int(os.getenv("PARDHA_RATE_LIMIT_MAX", "1000"))
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def enterprise_security_middleware(request: Request, call_next):
    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    bucket = _rate_buckets[client]
    while bucket and now - bucket[0] > _RATE_LIMIT_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _RATE_LIMIT_MAX_REQUESTS:
        return JSONResponse(status_code=status.HTTP_429_TOO_MANY_REQUESTS, content={"detail": "Rate limit exceeded."})
    bucket.append(now)
    response = await call_next(request)
    if request.url.path not in {"/enterprise/audit"}:
        try:
            record_audit(
                AuditEventCreate(
                    action=f"{request.method} {request.url.path}",
                    resource_type="api",
                    resource_id=request.url.path,
                    outcome="success" if response.status_code < 400 else "failed",
                    metadata={"status_code": response.status_code},
                ),
                ip_address=client,
                user_agent=request.headers.get("user-agent"),
            )
        except Exception:
            pass
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


@app.on_event("startup")
def startup_event():
    init_db()
    ensure_admin_user()
    if get_settings().mode == PardhaMode.DEVELOPMENT:
        ensure_demo_data()
    ensure_default_capabilities()
    ensure_enterprise_defaults()
    start_knowledge_watcher()
    start_scheduler()


@app.on_event("shutdown")
def shutdown_event():
    stop_knowledge_watcher()
    stop_scheduler()


@app.get("/")
def health():
    return {
        "name": "Pardha",
        "status": "alive"
    }


@app.post("/agents/register")
def create_agent(name: str, role: str):
    return register_agent(name, role)


@app.get("/agents")
def list_agents():
    return get_agents()


@app.post("/events", response_model=Event)
def publish_event_route(event: EventCreate):
    return publish_event(event)


@app.get("/events", response_model=list[Event])
def list_events_route(business_id: str | None = None):
    return get_events(business_id=business_id)


@app.get("/events/{agent_id}", response_model=list[Event])
def list_events_for_agent(agent_id: str, business_id: str | None = None):
    return get_events_by_agent(agent_id, business_id=business_id)


@app.post("/memories", response_model=Memory)
def save_memory_route(memory: MemoryCreate):
    return save_memory(memory)


@app.get("/memories", response_model=list[Memory])
def list_memories_route(business_id: str | None = None):
    return get_memories(business_id=business_id)


@app.get("/memories/search", response_model=list[Memory])
def search_memories_route(query: str, business_id: str | None = None):
    return search_memories(query, business_id=business_id)


@app.get("/memories/{agent_id}", response_model=list[Memory])
def list_memories_for_agent(agent_id: str, business_id: str | None = None):
    return get_memories_by_agent(agent_id, business_id=business_id)


@app.get("/agents/ceo/brief", response_model=DailyBrief)
def get_ceo_brief(business_id: str | None = None):
    return generate_daily_brief(business_id=business_id)


@app.get("/agents/cto/brief", response_model=CTOBrief)
def get_cto_brief(business_id: str | None = None):
    return generate_cto_brief(business_id=business_id)


@app.get("/agents/pm/brief", response_model=PMBrief)
def get_pm_brief(business_id: str | None = None):
    return generate_pm_brief(business_id=business_id)


@app.get("/test")
def test():
    return {
        "message": "Pardha Test Route"
    }
