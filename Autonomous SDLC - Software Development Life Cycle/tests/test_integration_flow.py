import os
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_integration_full_flow(monkeypatch):
    """
    Test d'intégration du flux complet : Réception Webhook -> CrewAI -> AutoGen -> Audit Log.
    Valide l'orchestration asynchrone et la génération physique du rapport Markdown.
    """
    # 1. Mocks des fonctions lourdes (LLM) pour isoler le test et le rendre instantané
    async def mock_run_architecture(request):
        return f"Plan technique simulé pour : {request}"
        
    async def mock_run_remediation(plan):
        return {
            "status": "success",
            "script_path": "/chemin/sandbox/script_remediation.py"
        }
        
    # Interception des appels dans app.main
    monkeypatch.setattr("app.main.run_architecture_phase", mock_run_architecture)
    monkeypatch.setattr("app.main.run_remediation_loop", mock_run_remediation)
    
    # 2. Préparation du payload de test avec un ID unique
    test_incident_id = f"TEST-INC-{int(datetime.now().timestamp())}"
    payload = {
        "incident_id": test_incident_id,
        "description": "Déployer un cluster Redis local"
    }
    
    # 3. Exécution de la requête POST
    # Note : Le TestClient de FastAPI exécute les BackgroundTasks de manière synchrone
    # juste avant de retourner la réponse, ce qui nous permet de tester l'effet de bord immédiatement.
    response = client.post("/orchestrate", json=payload)
    
    # 4. Validation des réponses API (DoD de l'US 1.1)
    assert response.status_code == 202
    assert response.json() == {"status": "accepted", "message": "Maestro request received"}
    
    # 5. Validation de la compétence Audit Logger (Système de fichiers)
    log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sandbox", "logs"))
    date_str = datetime.now().strftime("%Y-%m-%d")
    expected_filename = f"CR_{date_str}_{test_incident_id}.md"
    expected_path = os.path.join(log_dir, expected_filename)
    
    assert os.path.exists(expected_path), f"Le rapport d'audit {expected_filename} n'a pas été généré dans sandbox/logs/."
    
    # 6. Vérification du contenu du log (Garantie de bout en bout)
    with open(expected_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "✅ Succès" in content, "Le statut du log doit être un succès."
        assert "Plan technique simulé" in content, "Le log doit contenir le plan d'architecture."
        assert "script_remediation.py" in content, "Le log doit contenir le chemin du script généré."
        
    # Nettoyage du fichier de test
    os.remove(expected_path)
