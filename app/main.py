from fastapi import FastAPI

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

app = FastAPI(title="Pardha Kernel")


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
def list_events_route():
    return get_events()


@app.get("/events/{agent_id}", response_model=list[Event])
def list_events_for_agent(agent_id: str):
    return get_events_by_agent(agent_id)


@app.get("/test")
def test():
    return {
        "message": "Pardha Test Route"
    }
