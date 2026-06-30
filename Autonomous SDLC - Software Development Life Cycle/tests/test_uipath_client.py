import pytest
import asyncio
import httpx
from app.uipath.test_cloud_client import push_test_results_to_cloud

def test_push_results_auth_failure(monkeypatch):
    """
    Test SRE (Circuit Breaker) : Valide que l'échec de l'authentification (ex: token invalide)
    ne fait pas crasher l'application et retourne bien False de manière sécurisée.
    """
    # Simulation d'un échec d'authentification (jeton invalide ou connexion impossible)
    async def mock_get_token():
        return ""
        
    monkeypatch.setattr("app.uipath.test_cloud_client._get_access_token", mock_get_token)
    
    execution_data = {
        "status": "success", 
        "summary": "Mock execution", 
        "script_path": "script.sh"
    }
    
    # Exécution via asyncio.run pour éviter la dépendance stricte au plugin pytest-asyncio
    result = asyncio.run(push_test_results_to_cloud(execution_data))
    
    # L'erreur doit être logguée silencieusement et la fonction doit échouer proprement
    assert result is False, "La fonction doit renvoyer False lorsque le token n'est pas obtenu."

def test_push_results_success(monkeypatch):
    """
    Test Nominal : Valide qu'un envoi réussi vers l'API UiPath retourne True
    et que le payload JSON respecte le formalisme attendu par Test Manager.
    """
    # 1. Bouchonner la récupération du token
    async def mock_get_token():
        return "fake_valid_bearer_token"
        
    monkeypatch.setattr("app.uipath.test_cloud_client._get_access_token", mock_get_token)
    
    # 2. Bouchonner le client HTTPX pour intercepter la requête réseau sortante
    class MockResponse:
        def raise_for_status(self):
            pass # Simule un HTTP 200 OK
            
    class MockAsyncClient:
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
            
        async def post(self, url, json=None, data=None, headers=None, timeout=None):
            # Assertions dynamiques sur les requêtes interceptées
            assert headers["Authorization"] == "Bearer fake_valid_bearer_token"
            assert headers["Content-Type"] == "application/json"
            assert json["status"] == "Passed", "Le statut 'success' doit être mappé en 'Passed' pour Test Manager."
            assert "TC-AUTOGEN-01" in json["testCaseKey"]
            assert "/sandbox/deploy.sh" in json["artifacts"]
            return MockResponse()
            
    monkeypatch.setattr("httpx.AsyncClient", MockAsyncClient)
    
    execution_data = {
        "status": "success", 
        "summary": "Déploiement Docker réussi", 
        "script_path": "/sandbox/deploy.sh"
    }
    
    result = asyncio.run(push_test_results_to_cloud(execution_data))
    
    assert result is True, "La fonction doit renvoyer True lors d'une synchronisation réussie."
