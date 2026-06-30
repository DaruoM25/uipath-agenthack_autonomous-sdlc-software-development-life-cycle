import os
from typing import Dict, Any

def get_langchain_llm():
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GEMINI_API_KEY")
        return ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=api_key)
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        return ChatOpenAI(model="gpt-4o", openai_api_key=api_key)
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

def get_autogen_config() -> Dict[str, Any]:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider == "gemini":
        return {
            "config_list": [
                {
                    "model": "gemini-1.5-pro",
                    "api_key": os.getenv("GEMINI_API_KEY"),
                    "api_type": "google"
                }
            ]
        }
    elif provider == "openai":
        return {
            "config_list": [
                {
                    "model": "gpt-4o",
                    "api_key": os.getenv("OPENAI_API_KEY")
                }
            ]
        }
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

import logging
import httpx
import re
import json
from crewai import LLM

logger = logging.getLogger(__name__)

LLM_FALLBACK_CHAIN = [
    {"provider": "openrouter", "model": "openrouter/meta-llama/llama-3.3-70b-instruct", "api_key_env": "OPENROUTER_API_KEY"},
    {"provider": "groq", "model": "groq/llama-3.3-70b-versatile", "api_key_env": "GROQ_API_KEY"},
    {"provider": "ollama_cluster", "base_url": "http://localhost:11435", "dynamic_model": True, "timeout": 120},
    {"provider": "ollama_local", "model": "ollama/qwen2.5-coder:7b", "base_url": "http://localhost:11434", "lazy_start": True, "timeout": 120}
]

# Surcharge optionnelle via environnement pour modularité absolue
if os.getenv("LLM_FALLBACK_CHAIN"):
    try:
        LLM_FALLBACK_CHAIN = json.loads(os.getenv("LLM_FALLBACK_CHAIN"))
    except Exception as e:
        logger.error(f"Erreur de parsing de LLM_FALLBACK_CHAIN depuis .env: {e}")

def _discover_best_remote_model(base_url: str = "http://localhost:11435") -> str:
    """Découvre le meilleur modèle sur le cluster distant basé sur parameter_size."""
    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        response.raise_for_status()
        data = response.json()
        models = data.get("models", [])
        
        if not models:
            return "ollama/qwen2.5-coder:7b"
            
        def extract_size(model_info):
            size_str = model_info.get("details", {}).get("parameter_size", "0")
            match = re.search(r"([\d\.]+)", str(size_str))
            if match:
                val = float(match.group(1))
                if "M" in str(size_str).upper():
                    val /= 1000.0  # Convertir les millions en milliards
                return val
            return 0.0
            
        best_model = max(models, key=extract_size)
        model_name = best_model.get("name", "qwen2.5-coder:7b")
        return f"ollama/{model_name}"
    except Exception as e:
        logger.warning(f"Échec de découverte dynamique des modèles sur {base_url}: {e}. Fallback sur default.")
        return "ollama/qwen2.5-coder:7b"

def get_crewai_llm_with_failover() -> LLM:
    """
    Instancie un LLM pour CrewAI en utilisant un design pattern Circuit Breaker / Failover.
    
    Ce mécanisme teste séquentiellement la disponibilité des modèles suivants :
    1. Ollama Distant (tunnel k8s) (modèle dynamique sur 11435)
    2. Ollama Local (ollama/qwen2.5-coder:7b sur 11434)
    3. OpenRouter (openrouter/meta-llama/llama-3.1-8b-instruct)
    4. OpenAI (openai/gpt-4o-mini)
    5. Groq (groq/llama-3.3-70b-versatile)
    
    Une dégradation gracieuse est assurée : si l'instanciation ou le test
    d'un provider échoue (ex: erreur d'API, clé invalide), l'exception est
    interceptée, un avertissement est loggé, et la fonction passe
    automatiquement au modèle suivant.
    
    Returns:
        LLM: Une instance de la classe LLM de CrewAI opérationnelle.
        
    Raises:
        RuntimeError: Si tous les modèles de la chaîne échouent.
    """
    import time
    import subprocess
    import httpx
    
    for config in LLM_FALLBACK_CHAIN:
        provider = config.get("provider", "unknown")
        
        # Gestion du modèle dynamique
        if config.get("dynamic_model") and config.get("base_url"):
            model_name = _discover_best_remote_model(config["base_url"])
        else:
            model_name = config.get("model", "unknown-model")
            
        base_url = config.get("base_url")
        identifier = f"{model_name} ({base_url})" if base_url else model_name
        
        # Lazy start (Démarrage paresseux via Docker)
        if config.get("lazy_start") and base_url:
            logger.info(f"[FAILOVER] Tentative sur {provider}. Vérification du statut de l'instance locale...")
            try:
                httpx.get(base_url, timeout=2.0)
            except Exception:
                container_name = os.getenv("OLLAMA_CONTAINER_NAME", "ollama")
                logger.info(f"💤 Instance locale inactive. Tentative de réveil du conteneur Docker '{container_name}'...")
                try:
                    # 1. Démarrer le conteneur (ne fait rien s'il est déjà allumé)
                    subprocess.run(["docker", "start", container_name], check=True, capture_output=True, timeout=5.0)
                    
                    # 2. Boucle de Healthcheck pour s'assurer que l'API écoute et que le modèle charge
                    max_retries = 15
                    for attempt in range(max_retries):
                        try:
                            response = httpx.get(f"{base_url}/api/tags", timeout=2.0)
                            if response.status_code == 200:
                                logger.info("✅ Ollama Local est réveillé et prêt à opérer !")
                                break
                        except Exception:
                            pass
                            
                        logger.info(f"⏳ En attente de l'API Ollama locale... ({attempt + 1}/{max_retries})")
                        time.sleep(2)
                except subprocess.TimeoutExpired:
                    logger.error(f"❌ Timeout : Impossible de contacter le daemon Docker pour '{container_name}'.")
                except subprocess.CalledProcessError as e:
                    logger.error(f"❌ Impossible de démarrer le conteneur Docker '{container_name}': {e.stderr.decode() if e.stderr else str(e)}")
                except FileNotFoundError:
                    logger.error("❌ Docker n'est pas installé ou n'est pas dans le PATH.")
                        
        max_attempts = 4 if "ollama" in str(model_name).lower() or "ollama" in provider else 1
        
        for attempt in range(max_attempts):
            logger.info(f"[Failover Trace] Évaluation du provider: {identifier}")
            try:
                # Fast network check for Cloud providers
                if provider in ["openrouter", "groq", "openai"]:
                    try:
                        test_url = "https://openrouter.ai" if provider == "openrouter" else "https://api.groq.com"
                        httpx.get(test_url, timeout=2.0)
                    except Exception:
                        logger.warning(f"[FAILOVER] {provider} ignoré : Inaccessible via le réseau (Timeout/DNS).")
                        break
                        
                api_key = None
                if "api_key_env" in config:
                    api_key = os.getenv(config["api_key_env"])
                    if not api_key:
                        logger.warning(f"[FAILOVER] {provider} ignoré : clé API manquante ({config['api_key_env']}).")
                        break
                elif "api_key" in config:
                    api_key = config["api_key"]
                    
                kwargs = {"model": model_name}
                if api_key:
                    kwargs["api_key"] = api_key
                if base_url:
                    kwargs["base_url"] = base_url
                if "timeout" in config:
                    kwargs["timeout"] = config["timeout"]
                if "kwargs" in config:
                    # Injection des kwargs dynamiques
                    kwargs.update(config["kwargs"])
                    
                llm = LLM(**kwargs)
                llm.call(messages=[{"role": "user", "content": "ping"}])
                
                logger.info(f"[FAILOVER] {provider} OK -> Sélectionné ({identifier}).")
                return llm
                
            except Exception as e:
                error_str = str(e).lower()
                if ("ollama" in str(model_name).lower() or "ollama" in provider) and ("not found" in error_str or "404" in error_str):
                    if attempt < max_attempts - 1:
                        logger.warning(f"[FAILOVER] {provider} : Modèle en cours de chargement... ({e})")
                        time.sleep(10)
                        continue
                        
                # Formatage du log demandé pour les erreurs
                logger.warning(f"[FAILOVER] {provider} erreur -> Passage au suivant. Détails: {e}")
                break
                
    raise RuntimeError("Failover critique : Tous les LLMs configurés ont échoué.")

