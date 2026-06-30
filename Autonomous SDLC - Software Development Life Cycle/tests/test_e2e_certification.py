import pytest
import os
from unittest.mock import MagicMock
from app.agents.architect_crew import run_architecture_phase
from app.agents.engineer_loop import run_remediation_loop
from app.core.llm_factory import get_crewai_llm_with_failover
from crewai import LLM

@pytest.mark.anyio
async def test_orchestration_risk_low(monkeypatch):
    """Test 1 : Orchestration avec Risque Bas (Smoke Test)"""
    monkeypatch.setattr("app.agents.architect_crew.get_crewai_llm_with_failover", lambda: LLM(model="openai/gpt-4o-mini"))
    
    captured_tasks = []
    class MockCrewResult:
        def __str__(self):
            return "Spécifications: Caddy. Scénarios: curl HTTP 200 sur le port 80."

    async def mock_kickoff(self, *args, **kwargs):
        captured_tasks.extend(self.tasks)
        return MockCrewResult()

    monkeypatch.setattr("app.agents.architect_crew.Crew.kickoff_async", mock_kickoff)
    
    result = await run_architecture_phase("Configure un conteneur Caddy...", risk_level="Low")
    
    assert len(captured_tasks) == 3
    qa_task = captured_tasks[2]
    # Vérifie que la consigne pour Risque Bas est bien passée au LLM
    assert "Générer des Smoke Tests simples (vérification du port 80)" in qa_task.description
    assert "curl HTTP 200 sur le port 80" in str(result)

@pytest.mark.anyio
async def test_orchestration_risk_high(monkeypatch):
    """Test 2 : Orchestration avec Risque Élevé (Deep Test & Flaky)"""
    monkeypatch.setattr("app.agents.architect_crew.get_crewai_llm_with_failover", lambda: LLM(model="openai/gpt-4o-mini"))
    
    captured_tasks = []
    class MockCrewResult:
        def __str__(self):
            return "Spécifications: Caddy. Scénarios: Tests SSL/TLS, DDoS. Tests obsolètes ou fragiles potentiels: Test de charge 500 VUs."

    async def mock_kickoff(self, *args, **kwargs):
        captured_tasks.extend(self.tasks)
        return MockCrewResult()

    monkeypatch.setattr("app.agents.architect_crew.Crew.kickoff_async", mock_kickoff)
    
    result = await run_architecture_phase("Configure un conteneur Caddy...", risk_level="High")
    
    assert len(captured_tasks) == 3
    qa_task = captured_tasks[2]
    # Vérifie que la consigne pour Risque Élevé est bien passée au LLM
    assert "Générer des scripts de tests de charge et de sécurité complexes ET une section 'Analyse des Flaky Tests potentiels'" in qa_task.description
    assert "Tests SSL/TLS, DDoS" in str(result)
    assert "Tests obsolètes ou fragiles potentiels" in str(result)

@pytest.mark.anyio
async def test_remediation_loop_autogen(monkeypatch):
    """Test 3 : Validation de la boucle de remédiation (AutoGen)"""
    
    class MockChatResult:
        chat_history = [
            {"content": "Error: nginx configuration invalid"},
            {"content": "I fixed the configuration. Execution succeeded. TERMINATE"}
        ]
        
    async def mock_initiate_chat(self, recipient, message, summary_method):
        # Simule l'agent AutoGen identifiant l'erreur et générant un correctif puis TERMINATE
        return MockChatResult()
        
    monkeypatch.setattr("autogen.UserProxyAgent.a_initiate_chat", mock_initiate_chat)
    
    # Prépare un mock pour la création du fichier dans le sandbox afin d'éviter les erreurs
    monkeypatch.setattr("os.listdir", lambda path: ["script_fix.sh"])
    monkeypatch.setattr("os.path.abspath", lambda path: "/fake/sandbox")
    monkeypatch.setattr("os.makedirs", lambda path, exist_ok: None)
    
    result = await run_remediation_loop("Topologie avec erreur volontaire")
    
    assert result["status"] == "success"
    assert "script_fix.sh" in result["script_path"]

def test_circuit_breaker_resilience(monkeypatch):
    """Test 4 : Résilience des Flux IA (Le Circuit Breaker)"""
    monkeypatch.setenv("GROQ_API_KEY", "expired_key")
    monkeypatch.setenv("OPENAI_API_KEY", "expired_key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "expired_key")
    
    # Mock LLM.call pour lever une exception sur les API Cloud et réussir sur le local (Ollama)
    def mock_llm_call(self, messages):
        model_lower = self.model.lower()
        if "groq" in model_lower or "openai" in model_lower or "openrouter" in model_lower:
            raise Exception("HTTP 401 Unauthorized - Invalid API Key")
        # Ollama local réussit
        return "pong"
        
    monkeypatch.setattr("app.core.llm_factory.LLM.call", mock_llm_call)
    
    # Empêche le sleep pour accélérer le test si Ollama échouait, mais ici il réussit direct
    monkeypatch.setattr("time.sleep", lambda s: None)
    
    llm = get_crewai_llm_with_failover()
    
    # Vérifie que le fallback est allé jusqu'à Ollama
    assert "ollama" in llm.model.lower()
