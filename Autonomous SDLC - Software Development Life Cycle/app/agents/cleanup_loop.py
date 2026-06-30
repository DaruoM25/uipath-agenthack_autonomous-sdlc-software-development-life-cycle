import os
from autogen import AssistantAgent, UserProxyAgent
from autogen.coding import LocalCommandLineCodeExecutor
from app.core.llm_factory import get_autogen_config

async def run_cleanup_agent() -> str:
    """
    Déploie un agent AutoGen spécialisé pour nettoyer l'environnement (Docker et Workspace).
    Retourne la trace de la discussion et le résultat de l'exécution.
    """
    llm_config = get_autogen_config()
    
    is_terminate = lambda msg: "TERMINATE" in str(msg.get("content", "")).upper()
    
    custom_llm_config = {
        "config_list": [
            {
                "model": "qwen2.5-coder:7b",
                "base_url": "http://localhost:11434/v1",
                "api_key": "ollama",
            }
        ],
        "cache_seed": None,
    }

    # 1. Agent SRE de Nettoyage (Générateur de code)
    cleanup_agent = AssistantAgent(
        name="cleanup_agent",
        system_message=(
            "Tu es un agent SRE chargé du nettoyage de l'environnement. "
            "Ton rôle est de supprimer tous les conteneurs Docker créés pour le projet 'secure_node_app', "
            "de purger les images Docker orphelines, et de vider le dossier 'workspace_agents'. "
            "Génère un script Bash (dans un bloc markdown ```bash) avec la logique suivante :\n"
            "docker stop $(docker ps -a -q --filter ancestor=secure_node_app) 2>/dev/null || true\n"
            "docker rm $(docker ps -a -q --filter ancestor=secure_node_app) 2>/dev/null || true\n"
            "rm -rf workspace_agents/*\n\n"
            "IMPORTANT : Utilise toujours 'TERMINATE' à la fin de ta réponse finale une fois le script exécuté."
        ),
        llm_config=custom_llm_config,
        is_termination_msg=is_terminate,
    )

    # 2. Agent Testeur (Exécuteur de code)
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace_agents"))
    os.makedirs(workspace_dir, exist_ok=True)
    
    executor = LocalCommandLineCodeExecutor(
        timeout=120,
        work_dir=workspace_dir
    )

    cleanup_tester = UserProxyAgent(
        name="cleanup_tester",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=2,
        is_termination_msg=is_terminate,
        code_execution_config={"executor": executor},
        system_message="Exécute le code fourni par l'agent de nettoyage et rapporte les logs."
    )

    # 3. Lancement de la tâche
    prompt = "Exécute immédiatement le nettoyage complet de l'environnement Docker et de l'espace de travail."
    
    chat_result = await cleanup_tester.a_initiate_chat(
        cleanup_agent,
        message=prompt,
        summary_method="reflection_with_llm"
    )
    
    # Extraire les logs d'exécution (la réponse du testeur)
    execution_logs = ""
    for msg in chat_result.chat_history:
        if msg.get("name") == "cleanup_tester" and msg.get("content"):
            execution_logs += msg.get("content") + "\n"
            
    if not execution_logs.strip():
        execution_logs = "Exécution terminée. Voir la console pour les détails."

    return execution_logs
