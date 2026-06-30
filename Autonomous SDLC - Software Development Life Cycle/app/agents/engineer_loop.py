"""
Module implémentant la boucle de remédiation et de développement via AutoGen.
Définit les agents développeur et testeur pour la génération et la validation du code d'infrastructure.
"""

import os
from autogen import AssistantAgent, UserProxyAgent
from app.core.llm_factory import get_autogen_config

async def run_remediation_loop(plan: str, incident_id: str = "REQ-DEFAULT") -> dict:
    """
    Lance la boucle de remédiation AutoGen pour générer et tester un script d'infrastructure
    à partir d'un plan architectural.
    
    Args:
        plan (str): Le plan ou la topologie générée par la phase d'architecture.
        incident_id (str): Identifiant unique de l'incident pour lier le manifest.
        
    Returns:
        dict: Dictionnaire contenant le statut final et le chemin vers le script validé.
              Exemple: {"status": "success", "script_path": "/chemin/absolu/script.sh"}
              
    Raises:
        RuntimeError: Si la boucle atteint le nombre maximum de tentatives sans succès (boucle infinie cassée).
    """
    llm_config = get_autogen_config()

    # Définition de la condition d'arrêt basée sur le mot clé TERMINATE
    is_terminate = lambda msg: "TERMINATE" in str(msg.get("content", "")).upper()

    custom_llm_config = {
        "config_list": [
            {
                "model": "qwen2.5-coder:7b",
                "base_url": "http://localhost:11434/v1", # Endpoint OpenAI compatible d'Ollama
                "api_key": "ollama", # Clé fictive requise par AutoGen
            }
        ],
        "cache_seed": None, # Évite les bugs de cache
    }

    # 1. Création de l'agent développeur (LLM)
    infrastructure_developer = AssistantAgent(
        name="infrastructure_developer",
        system_message=(
            "Vous êtes un ingénieur DevOps/Infrastructure expert. "
            "Votre rôle est d'écrire des scripts (Bash, Python) robustes pour implémenter la topologie demandée et valider l'infrastructure. "
            "RÈGLES DE RUNTIME ET OUTILLAGE : "
            "1. L'agent testeur tourne sur WINDOWS. Tu n'es autorisé à générer QUE du code Python ou PowerShell (jamais de bash/sh). "
            "2. Si le plan QA inclut des scripts dans un langage non supporté (ex: Node.js), tu dois générer un script Python de bootstrap. "
            "   - Ce script Python doit écrire le code non supporté dans un fichier local puis l'exécuter. "
            "3. En cas d'erreur rapportée par le testeur, analysez les logs et ajustez vos scripts. "
            "4. Interdiction des arguments CLI : Tu ne dois JAMAIS écrire de scripts qui nécessitent des arguments en ligne de commande. "
            "5. Création de fichiers : Pour générer un fichier (JSON, YAML, etc.), utilise TOUJOURS un script Python simple qui écrit dans un fichier avec open('fichier', 'w'). Ne pas utiliser bash ni 'cat'. "
            "6. Séquence d'exécution : Fournis tes blocs de code en Python (```python) exclusivement, pour garantir la compatibilité Windows. "
            "7. Quand la suite de tests est validée par l'outil synthétisé avec un code de retour égal à 0, "
            "terminez IMPÉRATIVEMENT votre message par le mot 'TERMINATE'."
        ),
        llm_config=llm_config, # Utilise la config chargée dynamiquement (Gemini/OpenAI)
        is_termination_msg=is_terminate,
    )

    # 2. Configuration du dossier de travail strict
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace_agents", incident_id))
    os.makedirs(workspace_dir, exist_ok=True)
    
    from autogen.coding import LocalCommandLineCodeExecutor
    
    executor = LocalCommandLineCodeExecutor(
        timeout=120,
        work_dir=workspace_dir # Dossier isolé vital pour le futur nettoyage
    )

    # 3. Création de l'agent testeur (Exécuteur de code)
    infrastructure_tester = UserProxyAgent(
        name="infrastructure_tester",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=3,  # Robustesse : casse la boucle infinie après 3 allers-retours
        is_termination_msg=is_terminate,
        code_execution_config={"executor": executor},
        system_message="Vous êtes le testeur d'infrastructure. Exécutez le code fourni par le développeur et rapportez les logs ou erreurs."
    )

    # 4. Lancement de la discussion (Boucle de remédiation)
    prompt = f"""Générez, écrivez dans un fichier, et validez le code d'infrastructure correspondant au plan suivant :

{plan}

OBLIGATION CRITIQUE : Vous DEVEZ générer un script Python qui crée le fichier manifest de test (test_manifest_{incident_id}.json) contenant exactement la structure suivante, pour être exploité par UiPath Test Cloud. Renseignez les 'commands' avec vos propres scripts :
{{
  "incident_id": "{incident_id}",
  "test_set_name": "QA_Validation_Suite",
  "execution_mode": "test_cloud",
  "commands": [
    {{"type": "test", "script": "nom_de_votre_script.py"}}
  ],
  "requirements_mapping": ["{incident_id}"]
}}
"""
    
    chat_result = await infrastructure_tester.a_initiate_chat(
        infrastructure_developer,
        message=prompt,
        summary_method="reflection_with_llm"
    )

    # 5. Vérification du succès de la boucle (Recherche du signal TERMINATE)
    success = False
    for msg in reversed(chat_result.chat_history):
        if is_terminate(msg):
            success = True
            break
            
    if not success:
        raise RuntimeError("Échec Critique (Error Boundary) : Succès non atteint après 3 tentatives de remédiation AutoGen.")

    # 6. Recherche du fichier généré dans le workspace
    # En situation réelle, le nom du fichier serait retourné explicitement, ici on scanne le répertoire.
    generated_files = [f for f in os.listdir(workspace_dir) if not f.startswith('.')]
    script_path = os.path.join(workspace_dir, generated_files[0]) if generated_files else None

    return {
        "status": "success",
        "script_path": script_path
    }

async def run_external_remediation_loop(incident_id: str, test_logs: str) -> dict:
    """
    Agent de remédiation externe qui corrige le code existant suite à un échec dans UiPath Test Cloud.
    """
    llm_config = get_autogen_config()
    is_terminate = lambda msg: "TERMINATE" in str(msg.get("content", "")).upper()
    
    custom_llm_config = {
        "config_list": [{"model": "qwen2.5-coder:7b", "base_url": "http://localhost:11434/v1", "api_key": "ollama"}],
        "cache_seed": None,
    }

    infrastructure_developer = AssistantAgent(
        name="infrastructure_developer",
        system_message=(
            "Vous êtes un ingénieur DevOps expert en charge de la remédiation post-déploiement. "
            "Le test de l'infrastructure a échoué dans l'environnement distant (Test Cloud). "
            f"Voici votre mission pour l'incident {incident_id} :\n"
            "1. Lisez le code existant dans votre répertoire de travail.\n"
            "2. Analysez les logs d'échec fournis dans le message de l'utilisateur.\n"
            "3. Modifiez les scripts (en utilisant Python) pour corriger l'erreur.\n"
            f"4. Mettez à jour le fichier test_manifest_{incident_id}.json si nécessaire en utilisant Python.\n"
            "5. Votre réponse finale DOIT inclure un bloc JSON valide contenant la clé 'root_cause_analysis' expliquant la correction.\n"
            "6. Terminez par TERMINATE quand tout est corrigé."
        ),
        llm_config=llm_config,
        is_termination_msg=is_terminate,
    )

    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace_agents", incident_id))
    os.makedirs(workspace_dir, exist_ok=True)
    
    from autogen.coding import LocalCommandLineCodeExecutor
    executor = LocalCommandLineCodeExecutor(timeout=120, work_dir=workspace_dir)

    infrastructure_tester = UserProxyAgent(
        name="infrastructure_tester",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=3,
        is_termination_msg=is_terminate,
        code_execution_config={"executor": executor},
        system_message="Vous êtes le testeur local. Exécutez le code et vérifiez les corrections."
    )

    prompt = f"Voici les logs d'échec remontés par UiPath Test Cloud pour l'incident {incident_id} :\n\n{test_logs}\n\nAppliquez les corrections nécessaires et n'oubliez pas le bloc JSON root_cause_analysis."
    
    chat_result = await infrastructure_tester.a_initiate_chat(
        infrastructure_developer,
        message=prompt,
        summary_method="reflection_with_llm"
    )

    success = False
    for msg in reversed(chat_result.chat_history):
        if is_terminate(msg):
            success = True
            break
            
    if not success:
        raise RuntimeError("Échec Critique : Succès non atteint après 3 tentatives de remédiation.")

    # Extraction du root cause analysis
    rca = "Analyse non trouvée."
    for msg in reversed(chat_result.chat_history):
        content = msg.get("content", "")
        if "root_cause_analysis" in content:
            rca = content
            break

    return {
        "status": "success",
        "root_cause_analysis": rca
    }
