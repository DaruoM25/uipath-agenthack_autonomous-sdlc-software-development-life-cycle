import pytest
from pathlib import Path

def test_open_source_license():
    """Valide la présence et le contenu de la licence Open Source (MIT ou Apache 2.0)."""
    base_dir = Path(__file__).resolve().parent.parent
    
    license_file = base_dir / "LICENSE"
    license_md_file = base_dir / "LICENSE.md"
    
    assert license_file.exists() or license_md_file.exists(), "Erreur disqualifiante : Aucun fichier LICENSE ou LICENSE.md trouvé à la racine."
    
    target_file = license_file if license_file.exists() else license_md_file
    content = target_file.read_text(encoding="utf-8").lower()
    
    # Vérification textuelle
    is_mit = "mit license" in content or "permission is hereby granted" in content
    is_apache = "apache license" in content or "version 2.0" in content
    
    assert is_mit or is_apache, "Erreur disqualifiante : La licence n'est ni MIT ni Apache 2.0 valide."

def test_devpost_bonus_evidence():
    """Audit du README.md pour la présence des preuves de Coded Agents (Points Bonus Devpost)."""
    base_dir = Path(__file__).resolve().parent.parent
    readme_file = base_dir / "README.md"
    
    assert readme_file.exists(), "Erreur : Aucun fichier README.md trouvé à la racine."
    
    content = readme_file.read_text(encoding="utf-8")
    
    has_ai_assisted = "AI-Assisted Development" in content
    has_coded_agents = "Coded Agents Evidence" in content
    
    assert has_ai_assisted or has_coded_agents, "Erreur Devpost (Perte du Bonus Track 3) : Il manque les sections 'AI-Assisted Development' ou 'Coded Agents Evidence' dans le README.md."
