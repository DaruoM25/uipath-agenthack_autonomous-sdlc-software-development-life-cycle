import json

# Contenu d'exemple pour le manifeste de test
manifest_content = {
    "incident_id": "REQ-12345",
    "test_set_name": "QA_Validation_Suite",
    "execution_mode": "test_cloud",
    "commands": [
        {"type": "test", "script": "nom_de_votre_script.py"}
    ],
    "requirements_mapping": ["REQ-12345"]
}

# Écriture du fichier manifeste
with open('test_manifest_REQ-12345.json', 'w') as file:
    json.dump(manifest_content, file, indent=4)

print("Fichier manifeste de test créé avec succès : test_manifest_REQ-12345.json")