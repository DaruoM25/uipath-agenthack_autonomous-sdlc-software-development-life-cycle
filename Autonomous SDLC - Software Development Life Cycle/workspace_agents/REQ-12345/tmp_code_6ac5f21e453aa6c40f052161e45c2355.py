import json

# Define the data structure for test_manifest_REQ-12345.json
manifest_data = {
    "incident_id": "REQ-12345",
    "test_set_name": "QA_Validation_Suite",
    "execution_mode": "test_cloud",
    "commands": [
        {"type": "test", "script": "nom_de_votre_script.py"}
    ],
    "requirements_mapping": ["REQ-12345"]
}

# Write the data structure to a file
with open('test_manifest_REQ-12345.json', 'w') as f:
    json.dump(manifest_data, f, indent=4)

print("Manifest file test_manifest_REQ-12345.json created successfully.")