import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_orchestrate_performance_async():
    """Valide la délégation asynchrone et le retour 202 immédiat."""
    payload = {
        "incident_id": "INC-9999",
        "description": "Serveur de base de données inaccessible."
    }
    
    # Envoi d'une requête valide
    response = client.post("/orchestrate", json=payload)
    
    # Vérification du statut HTTP
    assert response.status_code == 202
    
    # Vérification du payload JSON
    assert response.json() == {"status": "accepted", "message": "Maestro request received"}

def test_orchestrate_resilience_error_boundary():
    """Valide la capture des erreurs (Error Boundary) pour empêcher l'exposition de stack trace."""
    # Envoi de données invalides (data string au lieu de json) pour provoquer une erreur lors du JSON parsing
    response = client.post("/orchestrate", data="Ce n'est pas un JSON valide")
    
    # Vérifie que l'erreur est bien catchée (Code 500 maîtrisé)
    assert response.status_code == 500
    
    # Vérifie que le retour est bien un JSON propre avec 'status: error'
    json_resp = response.json()
    assert "status" in json_resp
    assert json_resp["status"] == "error"
    assert "message" in json_resp
