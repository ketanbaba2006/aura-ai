"""
Quality Specialist Agents

Auto-registers all agents with the QualityOrchestrator on import.
"""

from app.quality.agents.base import BaseAgent, AgentFinding, AgentPatch, AgentReviewResult
from app.quality.agents.orchestrator import (
    QualityOrchestrator, register_agent, get_agent, list_agents,
    quality_orchestrator,
)
from app.quality.agents.architect import SoftwareArchitectAgent
from app.quality.agents.ui_designer import UIDesignerAgent
from app.quality.agents.frontend_dev import FrontendDeveloperAgent
from app.quality.agents.backend_dev import BackendDeveloperAgent
from app.quality.agents.db_specialist import DatabaseSpecialistAgent
from app.quality.agents.integration import IntegrationAgent
from app.quality.agents.qa_agent import QAAgent
from app.quality.agents.debugger import DebuggingAgent
from app.quality.agents.security import SecurityAgent

# Auto-instantiate and register all agents
_architect = SoftwareArchitectAgent()
_ui_designer = UIDesignerAgent()
_frontend_dev = FrontendDeveloperAgent()
_backend_dev = BackendDeveloperAgent()
_db_specialist = DatabaseSpecialistAgent()
_integration = IntegrationAgent()
_qa_agent = QAAgent()
_debugger = DebuggingAgent()
_security = SecurityAgent()

register_agent(_architect)
register_agent(_ui_designer)
register_agent(_frontend_dev)
register_agent(_backend_dev)
register_agent(_db_specialist)
register_agent(_integration)
register_agent(_qa_agent)
register_agent(_debugger)
register_agent(_security)

__all__ = [
    "BaseAgent",
    "AgentFinding",
    "AgentPatch",
    "AgentReviewResult",
    "QualityOrchestrator",
    "register_agent",
    "get_agent",
    "list_agents",
    "quality_orchestrator",
    "SoftwareArchitectAgent",
    "UIDesignerAgent",
    "FrontendDeveloperAgent",
    "BackendDeveloperAgent",
    "DatabaseSpecialistAgent",
    "IntegrationAgent",
    "QAAgent",
    "DebuggingAgent",
    "SecurityAgent",
]
