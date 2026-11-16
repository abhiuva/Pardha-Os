import uuid

from app.db import SessionLocal
from app.db.models import Agent as AgentModel


def _agent_to_dict(agent: AgentModel) -> dict:
    return {
        "id": agent.id,
        "name": agent.name,
        "role": agent.role,
        "status": agent.status,
    }


def register_agent(name: str, role: str):
    agent = AgentModel(
        id=str(uuid.uuid4()),
        name=name,
        role=role,
        status="active",
    )

    with SessionLocal() as session:
        session.add(agent)
        session.commit()
        session.refresh(agent)

    return _agent_to_dict(agent)


def get_agents():
    with SessionLocal() as session:
        agents = session.query(AgentModel).all()
    return [_agent_to_dict(agent) for agent in agents]
