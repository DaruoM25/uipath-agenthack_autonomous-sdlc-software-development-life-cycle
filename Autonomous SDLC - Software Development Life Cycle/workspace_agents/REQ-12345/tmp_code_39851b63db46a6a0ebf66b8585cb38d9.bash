cat << 'EOF' > script_correction.sh

function validate_dictionary {
  local dict_name=$1
  if ! eval "[[ -n \"\$$dict_name\" ]]" && [[ "$$dict_name" == *"{"*"}"* ]]; then
    echo "La variable '$dict_name' doit être un dictionnaire valide avec des clés présentes."
    exit 1
  fi
}

# Appeler cette fonction pour chaque dictionnaire utilisé.
validate_dictionary "nom_du_dictionnaire"

EOF