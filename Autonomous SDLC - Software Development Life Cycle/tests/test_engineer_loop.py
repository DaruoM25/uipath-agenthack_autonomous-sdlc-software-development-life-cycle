import pytest
import os
from app.agents.engineer_loop import run_remediation_loop

@pytest.mark.anyio
async def test_autogen_sandbox_config(monkeypatch):
    """
    Vérifie l'instanciation de l'agent testeur et s'assure que 
    la configuration de sécurité (Docker) et de robustesse (max_reply) est correcte.
    """
    captured_configs = {}
    
    class MockUserProxyAgent:
        def __init__(self, *args, **kwargs):
            captured_configs["max_consecutive_auto_reply"] = kwargs.get("max_consecutive_auto_reply")
            captured_configs["code_execution_config"] = kwargs.get("code_execution_config")
            
        async def a_initiate_chat(self, recipient, message, summary_method):
            class FakeChatResult:
                # Simule un succès immédiat pour laisser la fonction aller à son terme
                chat_history = [{"content": "The code runs fine. TERMINATE"}]
                summary = "Mock summary"
            return FakeChatResult()

    class MockAssistantAgent:
        def __init__(self, *args, **kwargs): pass

    # Mock total des agents AutoGen pour éviter de lancer Docker ou de requêter une API
    monkeypatch.setattr("app.agents.engineer_loop.UserProxyAgent", MockUserProxyAgent)
    monkeypatch.setattr("app.agents.engineer_loop.AssistantAgent", MockAssistantAgent)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "fake_key")
    
    # Exécution simulée de la boucle
    await run_remediation_loop("Plan technique")
    
    # Assertions mécaniques
    assert captured_configs["max_consecutive_auto_reply"] == 3, "La robustesse max_reply doit être à 3."
    
    code_config = captured_configs["code_execution_config"]
    assert code_config is not None, "Le code_execution_config ne doit pas être vide."
    assert code_config.get("use_docker") is True, "Sécurité: use_docker doit être forcé à True."
    assert "sandbox" in code_config.get("work_dir"), "Sécurité: Le dossier de travail doit cibler la sandbox."

@pytest.mark.anyio
async def test_remediation_loop_timeout_exception(monkeypatch):
    """
    Vérifie qu'un dépassement de quota (boucle sans succès)
    lève bien l'exception de sécurité attendue (RuntimeError).
    """
    class MockUserProxyAgentTimeout:
        def __init__(self, *args, **kwargs): pass
            
        async def a_initiate_chat(self, recipient, message, summary_method):
            class FakeChatResult:
                # Simule 3 échecs consécutifs sans jamais générer 'TERMINATE'
                chat_history = [
                    {"content": "SyntaxError: invalid syntax"}, 
                    {"content": "ModuleNotFoundError"}, 
                    {"content": "Still failing"}
                ]
                summary = "Failed"
            return FakeChatResult()

    class MockAssistantAgent:
        def __init__(self, *args, **kwargs): pass

    monkeypatch.setattr("app.agents.engineer_loop.UserProxyAgent", MockUserProxyAgentTimeout)
    monkeypatch.setattr("app.agents.engineer_loop.AssistantAgent", MockAssistantAgent)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "fake_key")
    
    # L'absence de 'TERMINATE' doit déclencher un RuntimeError sans geler le processus
    with pytest.raises(RuntimeError, match="Échec Critique"):
        await run_remediation_loop("Plan technique complexe")
