import json

# Define the test manifest structure
test_manifest = {
    "incident_id": "REQ-12345",
    "test_set_name": "QA_Validation_Suite",
    "execution_mode": "test_cloud",
    "commands": [
        {"type": "test", "script": "votre_script_de_tests.py"}
    ],
    "requirements_mapping": ["REQ-12345"]
}

# Write the manifest to a file
manifest_file_path = "test_manifest_REQ-12345.json"
with open(manifest_file_path, 'w') as f:
    json.dump(test_manifest, f, indent=4)

print(f"Manifest file '{manifest_file_path}' created successfully.")