try:
    logs = some_dict['logs']
except KeyError:
    logs = 'default_value_or_custom_exception("The required key \'logs\' is missing in the dictionary.")'