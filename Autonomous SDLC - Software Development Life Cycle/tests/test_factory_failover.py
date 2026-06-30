import pytest
import httpx
import time
from app.core.llm_factory import get_crewai_llm_with_failover

def test_get_crewai_llm_with_failover_fallback_to_ollama(monkeypatch):
    """
    Test d'intégration validant le comportement du Circuit Breaker.
    Simule l'absence de clés d'API cloud pour déclencher le failover
    et vérifie que la connexion avec le conteneur local Ollama est fonctionnelle.
    """
    # 1. Suppression forcée des clés d'API de l'environnement pour déclencher le failover
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    # 2. Boucle d'attente active (polling) pour s'assurer qu'Ollama est prêt et que le modèle est téléchargé
    max_retries = 24  # 24 * 5 = 120 secondes
    model_ready = False
    
    for i in range(max_retries):
        try:
            response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            if response.status_code == 200:
                tags = response.json()
                # Vérification stricte du tag exact attendu en production ET que le modèle est complètement extrait (size > 0)
                for model in tags.get("models", []):
                    if model.get("name", "") == "qwen2.5-coder:7b" and model.get("size", 0) > 0:
                        model_ready = True
                        break
                if model_ready:
                    break
        except httpx.RequestError:
            pass
        time.sleep(5)
        
    if not model_ready:
        pytest.fail("Timeout: Le conteneur Ollama n'est pas devenu stable avec le modèle qwen2.5-coder:7b après 120s.")

    # 3. Exécution de la fonction métier (le vrai ping de santé physique est exécuté !)
    llm = get_crewai_llm_with_failover()

    # 4. Assertions mécaniques
    assert llm is not None, "La Factory doit retourner une instance de LLM."
    assert "qwen2.5-coder:7b" in llm.model, f"Le modèle sélectionné aurait dû être Ollama, mais a été {llm.model}"
    assert "http://localhost:11434" in llm.base_url, f"L'URL de base d'Ollama est incorrecte: {llm.base_url}"
