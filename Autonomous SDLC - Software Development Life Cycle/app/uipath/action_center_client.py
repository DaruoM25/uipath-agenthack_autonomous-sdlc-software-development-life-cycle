"""
Module client pour l'API UiPath Action Center (Maestro).
Gère le pattern Human-in-the-Loop pour l'approbation finale des déploiements.
"""

import os
import logging
import httpx
from app.uipath.test_cloud_client import _get_access_token

logger = logging.getLogger(__name__)

UIPATH_MAESTRO_APPROVAL_URL = "https://staging.uipath.com/{organization}/{tenant}/orchestrator_/webhook/approval"

async def trigger_maestro_approval_state(task_id: str, audit_log_path: str) -> dict:
    """
    Déclenche la mise en attente d'approbation humaine dans UiPath Action Center.
    
    Args:
        task_id (str): L'identifiant de la tâche ou de l'incident.
        audit_log_path (str): Le chemin absolu ou relatif vers le fichier de log local.
        
    Returns:
        dict: Dictionnaire représentant l'état de la requête et les éventuelles données renvoyées.
    """
    token = await _get_access_token()
    
    organization = os.getenv("UIPATH_ORG_NAME", "default_org")
    tenant = os.getenv("UIPATH_TENANT_NAME", "a5191dbd-9a4f-4b12-9f04-8a5576227415")
    
    api_url = UIPATH_MAESTRO_APPROVAL_URL.format(organization=organization, tenant=tenant)
    
    payload = {
        "incident_id": task_id,
        "state": "PENDING_APPROVAL",
        "evidence_path": audit_log_path,
        "message": "Le déploiement généré par les agents IA requiert une validation humaine."
    }
    
    try:
        headers = {
            "Content-Type": "application/json"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
            
        logger.info(f"État PENDING_APPROVAL déclenché avec succès dans Action Center pour {task_id}.")
        return {"status": "success", "action_center_id": f"AC-{task_id}", "payload": payload}
        
    except httpx.RequestError as e:
        logger.error(f"Erreur réseau lors du déclenchement de l'approbation Maestro pour {task_id} : {e}")
        return {"status": "error", "message": "Network Error"}
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la mise en attente pour {task_id} : {e}")
        return {"status": "error", "message": str(e)}
