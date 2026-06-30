import sys
import os
from pathlib import Path

# Ajouter dynamiquement la racine du projet au sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
