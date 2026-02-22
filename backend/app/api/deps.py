from fastapi import Request
from app.services.live_system import LiveSystem
from app.core.persona import PersonaManager

def get_live_system(request: Request) -> LiveSystem:
    return request.app.state.live_system

def get_persona_manager(request: Request) -> PersonaManager:
    return request.app.state.persona_manager
