import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

@patch("app.main.run_architecture_phase")
def test_analyze_endpoint_success(mock_run):
    mock_run.return_value = "Plan d'architecture simulé"
    response = client.post("/analyze", json={"prompt": "Déployer nginx", "risk_level": "High", "environment": "prod"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "plan": "Plan d'architecture simulé"}

@patch("app.main.run_architecture_phase")
def test_analyze_endpoint_error(mock_run):
    mock_run.side_effect = Exception("Erreur LLM")
    response = client.post("/analyze", json={"prompt": "Déployer nginx", "risk_level": "High", "environment": "prod"})
    assert response.status_code == 500
    assert response.json()["status"] == "error"
    assert "Erreur LLM" in response.json()["message"]

def test_analyze_endpoint_mock():
    response = client.post("/analyze", json={"prompt": "Déployer nginx", "risk_level": "High", "environment": "dev"})
    assert response.status_code == 200
    assert "MOCK - MODE DEV" in response.json()["plan"]

@patch("app.main.run_remediation_loop")
def test_generate_artifacts_endpoint_success(mock_run):
    mock_run.return_value = {"status": "success", "script_path": "/tmp/script.sh"}
    response = client.post("/generate-artifacts", json={"plan": "Un plan", "incident_id": "REQ-123"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "result": {"status": "success", "script_path": "/tmp/script.sh"}}

@patch("app.main.run_remediation_loop")
def test_generate_artifacts_endpoint_error(mock_run):
    mock_run.side_effect = Exception("Erreur Generation")
    response = client.post("/generate-artifacts", json={"plan": "Un plan", "incident_id": "REQ-123"})
    assert response.status_code == 500

@patch("os.path.exists")
@patch("subprocess.run")
def test_validate_endpoint_success(mock_subprocess, mock_exists):
    mock_exists.return_value = True
    mock_process = MagicMock()
    mock_process.stdout = "Test OK"
    mock_process.stderr = ""
    mock_process.returncode = 0
    mock_subprocess.return_value = mock_process
    
    response = client.post("/validate", json={"script_path": "/path/to/script.sh"})
    assert response.status_code == 200

def test_validate_endpoint_not_found():
    with patch("os.path.exists", return_value=False):
        response = client.post("/validate", json={"script_path": "/path/to/script.sh"})
        assert response.status_code == 404

@patch("os.path.exists")
def test_validate_endpoint_error(mock_exists):
    mock_exists.side_effect = Exception("Erreur File System")
    response = client.post("/validate", json={"script_path": "/path/to/script.sh"})
    assert response.status_code == 500

@patch("app.main.run_external_remediation_loop")
def test_remediate_endpoint_success(mock_run):
    mock_run.return_value = {"status": "success", "root_cause_analysis": "Erreur de port"}
    response = client.post("/remediate", json={"incident_id": "REQ-123", "logs": "Error starting server"})
    assert response.status_code == 200

@patch("app.main.run_external_remediation_loop")
def test_remediate_endpoint_error(mock_run):
    mock_run.side_effect = Exception("Remediation error")
    response = client.post("/remediate", json={"incident_id": "REQ-123", "logs": "Error starting server"})
    assert response.status_code == 500

@patch("os.path.exists")
@patch("builtins.open")
@patch("json.load")
def test_get_test_suite_success(mock_json, mock_open, mock_exists):
    mock_exists.return_value = True
    mock_json.return_value = {"commands": []}
    response = client.get("/get-test-suite/REQ-123")
    assert response.status_code == 200

@patch("os.path.exists")
def test_get_test_suite_not_found(mock_exists):
    mock_exists.return_value = False
    response = client.get("/get-test-suite/REQ-123")
    assert response.status_code == 404

@patch("os.path.exists")
def test_get_test_suite_error(mock_exists):
    mock_exists.side_effect = Exception("IO Error")
    response = client.get("/get-test-suite/REQ-123")
    assert response.status_code == 500

@patch("os.path.exists")
@patch("builtins.open")
@patch("json.dump")
def test_report_test_result_success(mock_dump, mock_open, mock_exists):
    mock_exists.return_value = True
    response = client.post("/report-test-result", json={"incident_id": "REQ-123", "status": "SUCCESS", "logs": "All good"})
    assert response.status_code == 200

@patch("os.path.exists")
@patch("builtins.open")
@patch("json.dump")
def test_report_test_result_failed(mock_dump, mock_open, mock_exists):
    mock_exists.return_value = True
    response = client.post("/report-test-result", json={"incident_id": "REQ-123", "status": "FAILED", "logs": "Failed"})
    assert response.status_code == 200

@patch("os.path.exists")
def test_report_test_result_error(mock_exists):
    mock_exists.side_effect = Exception("DB Error")
    response = client.post("/report-test-result", json={"incident_id": "REQ-123", "status": "FAILED", "logs": "Failed"})
    assert response.status_code == 500

@patch("subprocess.run")
@patch("shutil.rmtree")
def test_rollback_workspace_success(mock_rmtree, mock_subprocess):
    response = client.post("/rollback")
    assert response.status_code == 200

@patch("os.path.exists")
@patch("shutil.rmtree")
def test_rollback_workspace_error(mock_rmtree, mock_exists):
    mock_exists.return_value = True
    mock_rmtree.side_effect = Exception("System error")
    response = client.post("/rollback")
    assert response.status_code == 500

def test_orchestrate_approve_success():
    response = client.post("/orchestrate/approve", json={"incident_id": "REQ-123", "approval_status": "APPROVED"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_orchestrate_approve_rejected():
    response = client.post("/orchestrate/approve", json={"incident_id": "REQ-123", "approval_status": "REJECTED"})
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
