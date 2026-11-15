# Pardha Performance Optimization Mode

Pardha defaults to `DEVELOPMENT` mode. Agents, objectives, and scheduler cycles
use deterministic logic and never invoke Ollama automatically.

Ollama runs only through:

- `POST /agents/ceo/reason`
- `POST /agents/cto/reason`
- `POST /agents/pm/reason`

The default request uses `llama3.2:3b`:

```json
{}
```

Advanced reasoning must be explicitly requested:

```json
{"model": "qwen3:8b"}
```

The manual endpoint starts the local Ollama daemon when needed. Requests are
serialized with `MAX_CONCURRENT_REASONING=1`, and `keep_alive: 0` unloads the
model after each response so Ollama returns to Idle.

Configuration:

```bash
PARDHA_MODE=DEVELOPMENT
PARDHA_OLLAMA_ENABLED=true
MAX_CONCURRENT_REASONING=1
```

Set `PARDHA_OLLAMA_ENABLED=false` to disable manual reasoning completely.
