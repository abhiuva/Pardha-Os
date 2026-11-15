from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ExecutiveCategory = Literal[
    "General Conversation",
    "General Knowledge",
    "Weather",
    "Coding",
    "Business",
    "Marketing",
    "Product",
    "Engineering",
    "Knowledge",
    "System",
    "Planning",
    "Memory",
    "Personal",
    "Execution",
]

ContextScope = Literal["none", "founder", "business", "marketing", "product", "engineering", "knowledge", "system", "planning", "execution"]
ReasoningRoute = Literal["deterministic", "business_capability", "ollama_qwen", "mcp_tool", "general_knowledge", "internet_tool"]


@dataclass(frozen=True)
class ExecutiveRoute:
    category: ExecutiveCategory
    intent: str
    context_scope: ContextScope
    reasoning_route: ReasoningRoute
    needs_business_context: bool
    needs_planner: bool = False
    needs_mcp: bool = False
    needs_internet: bool = False

    def model_dump(self) -> dict:
        return {
            "category": self.category,
            "intent": self.intent,
            "context_scope": self.context_scope,
            "reasoning_route": self.reasoning_route,
            "needs_business_context": self.needs_business_context,
            "needs_planner": self.needs_planner,
            "needs_mcp": self.needs_mcp,
            "needs_internet": self.needs_internet,
        }


def route_executive_intent(message: str) -> ExecutiveRoute:
    text = f" {message.lower().strip()} "

    if any(term in text for term in (" weather", "temperature", "forecast", "rain ", "snow ", "humidity")):
        return ExecutiveRoute("Weather", "weather", "none", "internet_tool", False, needs_internet=True)
    if any(term in text for term in ("what can you do", "how do you work", "available", "show what pardha can do")):
        return ExecutiveRoute("System", "system_health", "system", "business_capability", False)
    if any(term in text for term in ("model is active", "speech enabled", "microphone", "diagnostic", "health", "status", "connected", "connect ", "integration", "gmail", "jira", "whatsapp", "calendar", "github", "ollama", "voice", "system")):
        if any(term in text for term in ("dp360", "business health", "company health", "customer retention")):
            return ExecutiveRoute("Business", "business_review", "business", "business_capability", True)
        if any(term in text for term in ("repository health", "technical", "architecture", "backend", "frontend", "codebase")):
            return ExecutiveRoute("Engineering", "architecture_review", "engineering", "business_capability", True)
        return ExecutiveRoute("System", "system_health", "system", "business_capability", False)
    if any(term in text for term in (" hello", " hi ", " good morning", " good afternoon", " good evening", " thanks", "thank you")):
        return ExecutiveRoute("General Conversation", "general_conversation", "none", "deterministic", False)
    if any(term in text for term in ("planning preference", "meeting", "calendar preference", "schedule preference", "working style", "concise writing style")):
        return ExecutiveRoute("Personal", "personal_preference", "founder", "deterministic", False)
    if any(term in text for term in ("remember", "what did we decide", "what did i say", "my preference", "my writing style", "my style", "correction")):
        return ExecutiveRoute("Memory", "memory_review", "founder", "deterministic", False)
    if any(term in text for term in ("code", "python", "javascript", "react", "sql", "api", "function", "bug", "stack trace")) and not any(term in text for term in ("business", "dp360", "repository", "codebase", "engineering")):
        return ExecutiveRoute("Coding", "coding_assistance", "none", "ollama_qwen", False)
    if any(term in text for term in ("what is running", "execute", "execution", "approval", "approve", "rollback", "task", "blocked", "running", "queue")):
        return ExecutiveRoute("Execution", "execution_status", "execution", "business_capability", True)
    if any(term in text for term in ("define ", "what is", "who is", "explain", "teach me", "summarize")) and not any(term in text for term in ("company", "business", "customer retention", "dp360")):
        return ExecutiveRoute("General Knowledge", "general_knowledge", "none", "general_knowledge", False)
    if any(term in text for term in ("create a growth plan", "build a product roadmap", "launch a campaign plan", "growth plan")):
        return ExecutiveRoute("Planning", "planning_request", "planning", "business_capability", True, needs_planner=True)
    if any(term in text for term in ("engineering", "architecture", "backend", "frontend", "repository", "codebase", "technical", "service")):
        return ExecutiveRoute("Engineering", "architecture_review", "engineering", "business_capability", True)
    if any(term in text for term in ("knowledge", "document", "docs", "uploaded", "search", "find ", "retrieve")):
        return ExecutiveRoute("Knowledge", "knowledge_search", "knowledge", "business_capability", True)
    if any(term in text for term in ("marketing", "campaign", "content", "seo", "ads", "lead source", "ctr", "roas")):
        return ExecutiveRoute("Marketing", "marketing_summary", "marketing", "business_capability", True)
    if any(term in text for term in ("product", "prd", "roadmap", "feature", "backlog", "sprint")):
        return ExecutiveRoute("Product", "product_review", "product", "business_capability", True)
    if any(term in text for term in ("plan", "launch", "build", "create", "improve", "increase", "reduce", "acquire", "generate", "goal")):
        return ExecutiveRoute("Planning", "planning_request", "planning", "business_capability", True, needs_planner=True)
    if any(term in text for term in ("business", "company", "revenue", "growth", "retention", "customer", "sales", "pipeline", "brief", "summary", "review")):
        return ExecutiveRoute("Business", "business_review", "business", "business_capability", True)
    if any(term in text for term in ("what is", "who is", "explain", "define", "teach me", "summarize")):
        return ExecutiveRoute("General Knowledge", "general_knowledge", "none", "general_knowledge", False)
    return ExecutiveRoute("General Conversation", "general_conversation", "none", "deterministic", False)
