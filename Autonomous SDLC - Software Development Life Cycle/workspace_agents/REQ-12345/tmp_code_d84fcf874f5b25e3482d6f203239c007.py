config = {
    "service": "api-server",
    "input_data": { "log": "Ceci est un message de log" }
}

# Utilisation de get_logs pour obtenir les logs depuis config['input_data']
logs = get_logs(config['input_data'])

if logs is None:
    # Faire quelque chose si 'logs' est None, par exemple :
    logs = {}  # Affecter une valeur par défaut