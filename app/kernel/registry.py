import uuid

AGENTS = []

def register_agent(name: str, role: str):
    agent = {
        "id": str(uuid.uuid4()),
        "name": name,
        "role": role,
        "status": "active"
    }

    AGENTS.append(agent)

    return agent


def get_agents():
    return AGENTS