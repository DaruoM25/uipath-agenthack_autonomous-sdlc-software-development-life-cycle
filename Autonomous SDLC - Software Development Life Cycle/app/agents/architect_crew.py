"""
Module orchestrant la phase d'architecture via CrewAI.
Définit les agents et la logique de génération de topologie technique.
"""

from crewai import Agent, Task, Crew, Process, LLM
import os

from app.core.llm_factory import get_crewai_llm_with_failover

def get_architect_crew() -> Crew:
    """
    Configure et retourne l'équipe CrewAI pour la phase d'architecture.
    
    Returns:
        Crew: L'instance Crew configurée avec les agents SRE Manager et Infrastructure Architect.
    """
    llm = get_crewai_llm_with_failover()
    
    # Feature Flag: Mode de délégation dynamique
    # Par défaut, désactivé (False) pour protéger les LLMs locaux légers des erreurs de format
    ENABLE_AGENT_DELEGATION = os.getenv("ENABLE_AGENT_DELEGATION", "False").lower() in ("true", "1", "yes")

    sre_manager = Agent(
        role="SRE Manager",
        goal="Analyser les requêtes utilisateur et définir les exigences de fiabilité et de performance.",
        backstory="Expert en Site Reliability Engineering, garantissant que toute architecture proposée est robuste, scalable et hautement disponible.",
        verbose=True,
        allow_delegation=ENABLE_AGENT_DELEGATION,
        llm=llm
    )

    infra_architect = Agent(
        role="Infrastructure Architect",
        goal="Concevoir une topologie technique détaillée et actionnable basée sur les exigences du SRE Manager.",
        backstory="Architecte Cloud senior spécialisé dans la conception de solutions d'infrastructure optimisées et sécurisées.",
        verbose=True,
        allow_delegation=ENABLE_AGENT_DELEGATION,
        llm=llm
    )

    qa_agent = Agent(
        role="Lead QA Automation Engineer",
        goal="Évaluer les exigences et les transformer en scénarios de test significatifs, et identifier les tests fragiles (flaky tests).",
        backstory="Expert en assurance qualité et en tests automatisés, capable d'anticiper les défaillances et d'assurer la couverture de test maximale.",
        verbose=True,
        allow_delegation=ENABLE_AGENT_DELEGATION,
        llm=llm
    )

    return Crew(
        agents=[sre_manager, infra_architect, qa_agent],
        tasks=[],  # Les tâches seront ajoutées dynamiquement lors de l'exécution
        process=Process.sequential,
        verbose=True
    )

async def run_architecture_phase(user_request: str, risk_level: str = "High") -> str:
    """
    Orchestre une tâche séquentielle pour analyser une requête et générer une topologie technique.
    
    Args:
        user_request (str): La demande de l'utilisateur (ex: 'Déployer un serveur Nginx local').
        risk_level (str): Le niveau de risque ('Low' ou 'High').
        
    Returns:
        str: Le résultat final sous forme de topologie technique exploitable générée par les agents, incluant les scénarios QA.
    """
    crew = get_architect_crew()
    sre_manager = crew.agents[0]
    infra_architect = crew.agents[1]
    qa_agent = crew.agents[2]

    analysis_task = Task(
        description="Analyser la requête suivante pour en extraire les exigences techniques, de sécurité et de scalabilité : '{user_request}'",
        expected_output="Un document structuré détaillant les exigences techniques, de sécurité et de performance pour le déploiement.",
        agent=sre_manager
    )

    design_task = Task(
        description="À partir de l'analyse des exigences, générer une topologie technique exploitable. Inclure les composants, les réseaux, et les configurations nécessaires de manière détaillée.",
        expected_output="Une topologie technique complète et détaillée prête à être implémentée.",
        agent=infra_architect
    )

    # Tâche QA Automation Engineer
    qa_instruction = (
        "Générer des Smoke Tests simples (vérification du port 80)."
        if risk_level == "Low" else
        "Générer des scripts de tests de charge et de sécurité complexes ET une section 'Analyse des Flaky Tests potentiels'."
    )
    
    qa_task = Task(
        description=f"Prendre la topologie générée par l'Architecte et créer des tests adaptés au niveau de risque {risk_level}. Instructions : {qa_instruction}. IMPORTANT : Votre réponse finale DOIT inclure intégralement la topologie technique d'origine ET vos scénarios de test ajoutés à la fin.",
        expected_output="La topologie technique complète suivie des scénarios de test et de l'analyse QA.",
        agent=qa_agent
    )

    # Assigner les tâches à l'équipe
    crew.tasks = [analysis_task, design_task, qa_task]

    # Démarrer le processus de réflexion et de génération de manière asynchrone
    result = await crew.kickoff_async(inputs={"user_request": user_request})
    
    return str(result)
