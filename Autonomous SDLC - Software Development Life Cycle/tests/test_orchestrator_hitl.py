import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.uipath.action_center_client import trigger_maestro_approval_state

client = TestClient(app)

def test_trigger_maestro_approval_state(monkeypatch):
    """
    Test Unitaire : Valide que la demande d'approbation (Human-in-the-Loop)
    est correctement générée et que le client retourne le statut de mise en pause simulé
    sans émettre de vraie requête HTTP vers l'API UiPath.
    """
    # 1. Bouchonner la récupération du token SRE
    async def mock_get_token():
        return "fake_valid_token"
    monkeypatch.setattr("app.uipath.action_center_client._get_access_token", mock_get_token)
    
    # 2. Bouchonner le client HTTPX pour intercepter et valider la structure de la requête
    class MockResponse:
        def raise_for_status(self):
            pass # Simule un succès HTTP 200/201
            
    class MockAsyncClient:
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
            
        async def post(self, url, json=None, data=None, headers=None, timeout=None):
            # Assertions dynamiques sur le payload attendu par Maestro Action Center
            assert json["state"] == "PENDING_APPROVAL", "L'état du webhook doit imposer une pause d'approbation."
            assert json["incident_id"] == "INC-HITL-01"
            assert json["evidence_path"] == "/sandbox/logs/preuve.md"
            return MockResponse()
            
    monkeypatch.setattr("httpx.AsyncClient", MockAsyncClient)
    
    # 3. Exécution synchrone de la fonction asynchrone
    result = asyncio.run(trigger_maestro_approval_state("INC-HITL-01", "/sandbox/logs/preuve.md"))
    
    # 4. Assertions sur le retour de la fonction
    assert result["status"] == "success"
    assert result["action_center_id"] == "AC-INC-HITL-01"
    assert result["payload"]["state"] == "PENDING_APPROVAL"

def test_hitl_approval_webhook():
    """
    Test d'Intégration : Valide que l'endpoint /orchestrate/approve
    intercepte avec succès la décision humaine finale et renvoie un code HTTP 200
    sans faire crasher le webhook.
    """
    # --- Cas Nominal 1 : L'humain a cliqué sur "Approve" dans Action Center ---
    payload_approved = {
        "incident_id": "INC-HITL-01",
        "approval_status": "APPROVED"
    }
    
    response_approved = client.post("/orchestrate/approve", json=payload_approved)
    
    # Validation du retour HTTP pour Maestro
    assert response_approved.status_code == 200, "Le statut doit être 200 OK pour accuser réception de la validation."
    assert response_approved.json() == {"status": "success", "message": "Deployment finalized for INC-HITL-01"}
    
    # --- Cas Nominal 2 : L'humain a cliqué sur "Reject" dans Action Center ---
    payload_rejected = {
        "incident_id": "INC-HITL-02",
        "approval_status": "REJECTED"
    }
    
    response_rejected = client.post("/orchestrate/approve", json=payload_rejected)
    
    assert response_rejected.status_code == 200, "Un rejet humain est un flux valide, HTTP 200 OK est attendu."
    assert response_rejected.json() == {"status": "rejected", "message": "Deployment aborted for INC-HITL-02"}
