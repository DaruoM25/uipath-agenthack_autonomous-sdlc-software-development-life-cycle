#!/bin/bash

# Création du manifeste de test REQ-12345.json pour UiPath Test Cloud
cat << 'EOF' > test_manifest_REQ-12345.json
{
  "incident_id": "REQ-12345",
  "test_set_name": "QA_Validation_Suite",
  "execution_mode": "test_cloud",
  "commands": [
    {"type": "test", "script": "nom_de_votre_script.sh"}
  ],
  "requirements_mapping": ["REQ-12345"]
}
EOF

# Validation du manifeste de test
jq -e . < test_manifest_REQ-12345.json > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "Terminaison : Le manifeste de test a été créé et validé avec succès."
else
  echo "Erreur : Le manifeste de test est invalide."
  exit 1
fi