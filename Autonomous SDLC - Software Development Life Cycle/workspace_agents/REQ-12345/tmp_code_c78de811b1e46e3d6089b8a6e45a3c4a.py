...
def log_entry(key, value):
    if key in logs_dict:
        logs_dict[key].append(value)
    else:
        logs_dict[key] = [value]
...

# Ajout des paramètres "includeLogs" et "logLevel"
if kwargs.get('includeLogs'):
    for entry_type, entries_list in args._logs['entries'].items():
        log_entry(entry_type, entries_list)  # Ajout de ce qui manquait
...