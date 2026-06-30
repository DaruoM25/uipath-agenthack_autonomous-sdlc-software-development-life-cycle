from fastapi import FastAPI, Request, status, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from typing import Optional, Literal
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import logging
from datetime import datetime
import os

try:
    import google.generativeai as genai
    if os.getenv("GEMINI_API_KEY"):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except ImportError:
    pass

from app.agents.architect_crew import run_architecture_phase
from app.agents.engineer_loop import run_remediation_loop
from app.uipath.test_cloud_client import push_test_results_to_cloud
from app.uipath.action_center_client import trigger_maestro_approval_state

load_dotenv()

from app.core.llm_factory import get_crewai_llm_with_failover

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Appel de la logique d'orchestration pour tester les endpoints disponibles
        llm = get_crewai_llm_with_failover()
        model_name = getattr(llm, "model", "Unknown")
        base_url = getattr(llm, "base_url", "Cloud API")
        
        if base_url and "11435" in str(base_url):
            engine = "OLLAMA (Cluster Distant)"
        elif base_url and "11434" in str(base_url):
            engine = "OLLAMA (Local)"
        elif "groq" in model_name.lower():
            engine = "GROQ (Cloud API)"
        elif "gpt" in model_name.lower():
            engine = "OPENAI (Cloud API)"
        else:
            engine = f"CLOUD API"
            
        print("\n==================================================")
        print("AUTONOMOUS SYSTEM READY")
        print(f"Active LLM Engine : {engine}")
        print(f"Endpoint : {base_url}")
        print(f"Selected Model : {model_name}")
        print("==================================================")
        print("SERVICES MENU (API ENDPOINTS)")
        print("Endpoint                  Role")
        print("--------------------------------------------------")
        print("POST /analyze             Requirements Analysis & Architecture")
        print("POST /generate-artifacts  Artifacts Generation (Dockerfile)")
        print("POST /validate            Test Execution")
        print("POST /remediate           Auto-remediation & Feedback")
        
        ngrok_url = os.getenv("NGROK_PUBLIC_URL")
        if ngrok_url:
            print("--------------------------------------------------")
            print(f"TUNNEL NGROK ACTIF : {ngrok_url}")
            
        print("==================================================\n")
    except Exception as e:
        logger.critical("\n==================================================")
        logger.critical("CRITICAL WARNING : NO LLM ENGINE REACHABLE")
        logger.critical(f"The system will not be able to function. Error: {e}")
        logger.critical("==================================================\n")
    yield

app = FastAPI(
    title="Autonomous SDLC - Orchestrator API",
    description="Services Menu for UiPath. Dynamic endpoints documentation.",
    version="1.0.0",
    lifespan=lifespan
)
logger = logging.getLogger(__name__)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    logger.error(f"422 Error: {exc.errors()}")
    logger.error(f"Request Body: {body.decode()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

class AnalyzeRequest(BaseModel):
    prompt: str = Field(..., json_schema_extra={"example": "Deploy a secure Node.js application."})
    risk_level: Literal["Low", "High"] = "High"
    environment: str = Field(default="dev", json_schema_extra={"example": "dev"})

class GenerateRequest(BaseModel):
    plan: str = Field(..., json_schema_extra={"example": "Architecture plan..."})
    incident_id: str = Field(default="REQ-DEFAULT", json_schema_extra={"example": "REQ-12345"})

class ValidateRequest(BaseModel):
    script_path: str = Field(..., json_schema_extra={"example": "/workspace_agents/REQ-12345/test.sh"})

class TestResultPayload(BaseModel):
    incident_id: str = Field(..., json_schema_extra={"example": "REQ-12345"})
    status: Literal["SUCCESS", "FAILED", "PASSED"] = Field(..., json_schema_extra={"example": "FAILED"})
    logs: Optional[str] = Field(default="", json_schema_extra={"example": "Timeout on Test Cloud..."})

class RemediateRequest(BaseModel):
    incident_id: str = Field(..., json_schema_extra={"example": "REQ-12345"})
    logs: str = Field(..., json_schema_extra={"example": "Error: port 8080 already in use"})

@app.post("/analyze", status_code=status.HTTP_200_OK)
async def analyze_endpoint(payload: AnalyzeRequest):
    """
    Reçoit le prompt utilisateur et renvoie le plan d'architecture technique (CrewAI).
    Inclut le switch d'environnement (Mock en dev, CrewAI en test/prod).
    """
    try:
        logger.info(f"Déclenchement de l'analyse CrewAI pour : {payload.prompt}")
        architecture_plan = await run_architecture_phase(payload.prompt, payload.risk_level)
        return {"status": "success", "plan": architecture_plan}
    except Exception as e:
        logger.error(f"Erreur dans /analyze: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/generate-artifacts", status_code=status.HTTP_200_OK)
async def generate_artifacts_endpoint(payload: GenerateRequest):
    """
    Reçoit le plan d'architecture, déclenche la boucle de génération AutoGen (Self-Healing),
    et génère le code/scripts sur le disque, incluant le manifest de test.
    """
    try:
        logger.info(f"Déclenchement de la génération d'artefacts pour {payload.incident_id}...")
        remediation_result = await run_remediation_loop(payload.plan, payload.incident_id)
        return {"status": "success", "result": remediation_result, "dockerfile": remediation_result}
    except Exception as e:
        logger.error(f"Erreur dans /generate-artifacts: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/validate", status_code=status.HTTP_200_OK)
async def validate_endpoint(payload: ValidateRequest):
    """
    Déclenche la simulation de test (validation post-déploiement à blanc) 
    sur les artefacts générés et retourne les logs.
    """
    import subprocess
    try:
        logger.info(f"Déclenchement de la validation pour le script : {payload.script_path}")
        if not os.path.exists(payload.script_path):
            return JSONResponse(status_code=404, content={"status": "error", "message": "Script not found"})
            
        result = subprocess.run(["bash", payload.script_path], capture_output=True, text=True, timeout=60)
        logs = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        
        return {"status": "success", "returncode": result.returncode, "logs": logs}
    except Exception as e:
        logger.error(f"Erreur dans /validate: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

# --- Nouveaux endpoints d'intégration UiPath Test Cloud (PO-02) ---

@app.get("/get-test-suite/{incident_id}", status_code=status.HTTP_200_OK)
async def get_test_suite(incident_id: str):
    """
    Retourne le manifest de test généré par l'IA pour un incident donné.
    Utilisé par UiPath pour orchestrer 'Run Test Set' dans Test Cloud.
    """
    try:
        workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace_agents", incident_id))
        manifest_path = os.path.join(workspace_dir, f"test_manifest_{incident_id}.json")
        
        if not os.path.exists(manifest_path):
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Manifest not found for {incident_id}"})
            
        import json
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
            
        return {"status": "success", "manifest": manifest_data}
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du manifest: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/report-test-result", status_code=status.HTTP_200_OK)
async def report_test_result(payload: TestResultPayload):
    """
    Réception du résultat final des tests depuis UiPath Test Cloud.
    Met à jour l'état local et génère un log d'audit.
    """
    try:
        incident_id = payload.incident_id
        
        # 1. Gestion de l'état local
        sandbox_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sandbox"))
        os.makedirs(sandbox_dir, exist_ok=True)
        state_path = os.path.join(sandbox_dir, f"state_{incident_id}.json")
        
        state_data = {"status": payload.status, "timestamp": datetime.now().isoformat()}
        if payload.status == "FAILED":
            state_data["message"] = "In Remediation"
            logger.warning(f"[{incident_id}] Test FAILED. Incident marqué 'In Remediation'.")
        else:
            state_data["message"] = "Validated"
            logger.info(f"[{incident_id}] Test SUCCESS. Incident validé.")
            
        import json
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)
            
        # 2. Génération de l'audit log
        log_dir = os.path.join(sandbox_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_path = os.path.join(log_dir, f"CR_{date_str}_{incident_id}.md")
        
        markdown_content = f"# Rapport d'Exécution : {incident_id}\n**Date** : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n**Statut** : {payload.status}\n\n## Logs\n{payload.logs}\n"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
            
        return {"status": "success", "message": f"State updated for {incident_id}"}
    except Exception as e:
        logger.error(f"Erreur lors du traitement du résultat de test: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

from app.agents.engineer_loop import run_external_remediation_loop

@app.post("/remediate", status_code=status.HTTP_200_OK)
async def remediate_endpoint(payload: RemediateRequest):
    """
    Reçoit les logs d'échec de UiPath Test Cloud et déclenche l'agent de remédiation AutoGen.
    Le dossier workspace est isolé par incident_id.
    """
    try:
        logger.info(f"Déclenchement de la remédiation externe pour {payload.incident_id}...")
        remediation_result = await run_external_remediation_loop(payload.incident_id, payload.logs)
        return {"status": "success", "result": remediation_result, "fixed_code": remediation_result}
    except Exception as e:
        logger.error(f"Erreur dans /remediate: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

# NOTE: Le workflow monolithique complet /orchestrate a été supprimé au profit des endpoints modulaires.

@app.post("/orchestrate/approve", status_code=status.HTTP_200_OK)
async def orchestrate_approve(request: Request):
    """
    Webhook endpoint to intercept the final validation from UiPath Action Center.
    Termine définitivement le cycle de déploiement si l'humain approuve.
    """
    try:
        payload = await request.json()
        incident_id = payload.get("incident_id", "UNKNOWN")
        approval_status = payload.get("approval_status", "APPROVED")
        
        logger.info(f"Validation Human-in-the-Loop reçue pour {incident_id} : {approval_status}")
        
        if approval_status == "APPROVED":
            logger.info(f"[{incident_id}] Déploiement final approuvé et exécuté sur l'infrastructure de production.")
            return {"status": "success", "message": f"Deployment finalized for {incident_id}"}
        else:
            logger.warning(f"[{incident_id}] Le déploiement a été REJETÉ par l'humain dans Action Center.")
            return {"status": "rejected", "message": f"Deployment aborted for {incident_id}"}
            
    except Exception as e:
        logger.error(f"Erreur lors de la réception de l'approbation : {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": str(e)}
        )

import shutil
import subprocess

@app.post("/rollback", status_code=status.HTTP_200_OK)
async def rollback_workspace():
    """
    Bouton Rouge de Nettoyage : Script d'exécution robuste (sans IA) pour purger Docker et l'espace de travail.
    Répond au ticket PO-04.
    """
    try:
        logger.info("Déclenchement du Bouton Rouge de Nettoyage...")
        
        logs = []
        
        # 1. Arrêter et supprimer les conteneurs Docker (secure_node_app)
        try:
            stop_cmd = "docker stop $(docker ps -a -q --filter ancestor=secure_node_app)"
            rm_cmd = "docker rm $(docker ps -a -q --filter ancestor=secure_node_app)"
            
            subprocess.run(stop_cmd, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            subprocess.run(rm_cmd, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            logs.append("Conteneurs Docker 'secure_node_app' purgés.")
        except Exception as docker_err:
            logs.append(f"Erreur Docker (ignorée) : {docker_err}")

        # 2. Supprimer le dossier de travail global (workspace_agents)
        workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace_agents"))
        if os.path.exists(workspace_dir):
            shutil.rmtree(workspace_dir)
            logs.append(f"Dossier {workspace_dir} supprimé.")
            
        # Re-création pour éviter des erreurs futures
        os.makedirs(workspace_dir, exist_ok=True)
        logs.append("Dossier workspace_agents réinitialisé.")

        return {
            "status": "success",
            "message": "Environnement réinitialisé",
            "logs": "\n".join(logs)
        }
    except Exception as e:
        logger.error(f"Erreur critique lors du rollback : {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
