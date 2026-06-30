import os
import pytest
from pathlib import Path
from app.core.llm_factory import get_langchain_llm, get_autogen_config
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

def test_structure_integrity():
    """Vérifie la présence physique des répertoires clés."""
    base_dir = Path(__file__).resolve().parent.parent
    
    required_dirs = [
        "app/core",
        "app/agents",
        "app/tools",
        "app/uipath",
        "sandbox/logs"
    ]
    
    for dir_path in required_dirs:
        target_path = base_dir / dir_path
        assert target_path.exists() and target_path.is_dir(), f"Erreur critique : Le répertoire {dir_path} est introuvable."

def test_gemini_factory(monkeypatch):
    """Vérifie l'isolation de l'environnement pour Gemini."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "fake_key")
    
    # Validation LangChain
    llm = get_langchain_llm()
    assert isinstance(llm, ChatGoogleGenerativeAI), "Le Factory n'a pas retourné une instance de ChatGoogleGenerativeAI"
    
    # Validation AutoGen Config
    config = get_autogen_config()
    assert "config_list" in config
    assert len(config["config_list"]) > 0
    assert config["config_list"][0]["model"] == "gemini-1.5-pro"
    assert config["config_list"][0]["api_key"] == "fake_key"
    assert config["config_list"][0]["api_type"] == "google"

def test_openai_factory(monkeypatch):
    """Vérifie le basculement élastique sur OpenAI."""
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "fake_key")
    
    # Validation LangChain
    llm = get_langchain_llm()
    assert isinstance(llm, ChatOpenAI), "Le Factory n'a pas basculé sur une instance de ChatOpenAI"
    
    # Validation AutoGen Config
    config = get_autogen_config()
    assert "config_list" in config
    assert len(config["config_list"]) > 0
    assert config["config_list"][0]["model"] == "gpt-4o"
    assert config["config_list"][0]["api_key"] == "fake_key"

def test_factory_error_boundary(monkeypatch):
    """Vérifie la levée d'exception pour un provider inconnu."""
    monkeypatch.setenv("LLM_PROVIDER", "unknown_ai")
    
    with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER: unknown_ai"):
        get_langchain_llm()
        
    with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER: unknown_ai"):
        get_autogen_config()
