def get_logs(input_dict):
    if 'logs' in input_dict:
        return input_dict['logs']
    else:
        print("Avertissement : La clé 'logs' n'est pas présente dans le dictionnaire input.")
        return None

# Exemple d'utilisation
input_data = { "log": "Ceci est un message de log" }
logs = get_logs(input_data)