"""
Module client pour l'API UiPath Test Cloud.
Gère l'authentification OAuth et la synchronisation des résultats d'exécution des agents.
Conçu avec des principes SRE : fail-safe, asynchrone, et non-bloquant.
"""

import os
import logging
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

# Endpoints UiPath de démonstration
UIPATH_OAUTH_URL = "https://staging.uipath.com/identity_/connect/token"
UIPATH_TEST_MANAGER_URL = "https://staging.uipath.com/{organization}/{tenant}/testmanager_/api/v1/testcases/execution"

async def _get_access_token() -> str:
    """
    Récupère un jeton d'accès OAuth depuis le serveur d'identité UiPath.
    
    Returns:
        str: Le token Bearer, ou une chaîne vide en cas d'échec.
    """
    client_id = os.getenv("UIPATH_CLIENT_ID")
    client_secret = os.getenv("UIPATH_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        logger.warning("SRE Warning : Identifiants UiPath (CLIENT_ID/CLIENT_SECRET) manquants. Impossible de générer le token OAuth.")
        return ""

    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "TestManager.TestExecution.Write"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(UIPATH_OAUTH_URL, data=payload, timeout=5.0)
            response.raise_for_status()
            return response.json().get("access_token", "")
    except Exception as e:
        logger.error(f"SRE Alert : Erreur lors de la récupération du token UiPath : {e}")
        return ""

async def push_test_results_to_cloud(execution_data: dict) -> bool:
    """
    Envoie les résultats d'exécution AutoGen vers UiPath Test Cloud de manière asynchrone.
    
    Circuit Breaker pattern appliqué : cette fonction est conçue pour être 'fail-safe' (non bloquante). 
    Toute erreur réseau ou d'authentification sera interceptée et logguée silencieusement 
    sans jamais faire crasher le workflow principal (Error Boundary strict).
    
    Args:
        execution_data (dict): Dictionnaire contenant les résultats d'exécution (status, summary, script_path).
                               
    Returns:
        bool: True si l'envoi a réussi, False en cas d'échec silencieux.
    """
    try:
        token = await _get_access_token()
        if not token:
            logger.error("Synchronisation UiPath abandonnée : Token OAuth indisponible.")
            return False

        organization = os.getenv("UIPATH_ORG_NAME", "default_org")
        tenant = os.getenv("UIPATH_TENANT_NAME", "default_tenant")
        
        api_url = UIPATH_TEST_MANAGER_URL.format(organization=organization, tenant=tenant)
        
        # Formatage standard du JSON Test Case pour UiPath Test Cloud
        mapped_status = "Passed" if execution_data.get("status") == "success" else "Failed"
        
        payload = {
            "testCaseKey": "TC-AUTOGEN-01",
            "status": mapped_status,
            "executionTime": datetime.now().isoformat(),
            "summary": execution_data.get("summary", "Exécution de remédiation technique AutoGen"),
            "artifacts": [execution_data.get("script_path")] if execution_data.get("script_path") else []
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Appel API asynchrone avec Timeout SRE de 10s
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
            
        logger.info("✅ Résultats des tests synchronisés avec succès vers UiPath Test Cloud.")
        return True
        
    except httpx.RequestError as exc:
        logger.error(f"SRE Alert : Erreur réseau critique lors de la communication avec UiPath Test Cloud : {exc}")
        return False
    except httpx.HTTPStatusError as exc:
        logger.error(f"SRE Alert : Erreur API UiPath (Statut {exc.response.status_code}) : {exc.response.text}")
        return False
    except Exception as exc:
        logger.error(f"SRE Alert : Exception inattendue lors de la synchronisation UiPath : {exc}")
        return False
