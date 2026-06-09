from fastapi import FastAPI

from app.kernel.registry import (
    register_agent,
    get_agents
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

@app.get("/test")
def test():
    return {
        "message": "Pardha Test Route"
    }