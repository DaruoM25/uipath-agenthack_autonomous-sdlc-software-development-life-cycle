import pytest
from app.agents.architect_crew import run_architecture_phase

@pytest.mark.anyio
async def test_architect_crew_execution(monkeypatch):
    """
    Test unitaire pour s'assurer que la phase d'architecture s'exécute correctement
    et retourne une spécification d'infrastructure sans appeler réellement l'API LLM externe.
    """
    # 1. Configuration de l'environnement virtuel pour la Factory (Agnosticisme LLM)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "fake_key_for_test")

    # 2. Mock de la Factory pour satisfaire la validation Pydantic de l'Agent
    from crewai import LLM
    monkeypatch.setattr(
        "app.agents.architect_crew.get_crewai_llm_with_failover", 
        lambda: LLM(model="openai/gpt-4o-mini")
    )

    # Mock léger de la méthode kickoff_async de Crew pour éviter l'exécution des agents
    class MockCrewResult:
        def __str__(self):
            return "Spécifications d'infrastructure : 1x Load Balancer Nginx, 2x App Servers, 1x Base de données PostgreSQL sécurisée."
            
    async def mock_kickoff(*args, **kwargs):
        return MockCrewResult()

    monkeypatch.setattr("app.agents.architect_crew.Crew.kickoff_async", mock_kickoff)

    # 3. Exécution de la fonction métier avec une requête utilisateur
    user_request = "Déployer une application web avec Nginx et une base de données"
    result = await run_architecture_phase(user_request)

    # 4. Assertions mécaniques
    assert isinstance(result, str), "Le résultat retourné doit être une chaîne de caractères."
    assert len(result) > 0, "Le résultat de l'architecture ne doit pas être vide."
    assert "Spécifications d'infrastructure" in result, "Le résultat doit contenir les spécifications demandées."
    assert "Nginx" in result, "Le résultat doit inclure les composants demandés par l'utilisateur."
