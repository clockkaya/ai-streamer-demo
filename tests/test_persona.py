import pytest
from unittest.mock import patch, MagicMock
from app.core.persona import PersonaManager, PersonaBundle, PersonaConfig, TTSConfig, RAGConfig

@pytest.fixture
def mock_persona_config():
    return PersonaConfig(
        name="Test",
        description="A test persona",
        system_prompt="You are a test",
        tts=TTSConfig(voice="test"),
        rag=RAGConfig()
    )

def test_default_persona_id_with_is_default(mock_persona_config):
    manager = PersonaManager()
    
    # Create a non-default persona
    config1 = mock_persona_config.model_copy()
    config1.is_default = False
    bundle1 = PersonaBundle(config1, MagicMock())
    
    # Create a default persona
    config2 = mock_persona_config.model_copy()
    config2.is_default = True
    bundle2 = PersonaBundle(config2, MagicMock())
    
    manager._personas = {
        "persona1": bundle1,
        "persona2": bundle2
    }
    
    assert manager.default_persona_id == "persona2"

def test_default_persona_id_without_is_default(mock_persona_config):
    manager = PersonaManager()
    
    # Create non-default personas
    config1 = mock_persona_config.model_copy()
    config1.is_default = False
    bundle1 = PersonaBundle(config1, MagicMock())
    
    config2 = mock_persona_config.model_copy()
    config2.is_default = False
    bundle2 = PersonaBundle(config2, MagicMock())
    
    # Dictionaries are ordered by insertion in Python 3.7+, so it should pick the first inserted
    manager._personas = {
        "persona1": bundle1,
        "persona2": bundle2
    }
    
    assert manager.default_persona_id == "persona1"

def test_default_persona_id_empty():
    manager = PersonaManager()
    manager._personas = {}
    
    with pytest.raises(ValueError, match="系统中没有加载任何角色"):
        _ = manager.default_persona_id
