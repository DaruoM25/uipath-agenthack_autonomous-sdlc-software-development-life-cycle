# ---- Étape 1 : Build & Test (Stage de validation) ----
FROM python:3.10-slim AS builder

WORKDIR /app

# Copie du fichier de dépendances
COPY requirements.txt .

# Installation de TOUTES les dépendances (y compris pytest, httpx pour les tests)
RUN pip install --no-cache-dir -r requirements.txt

# Copie de l'ensemble du projet (y compris le dossier tests/)
COPY . .

# Variables d'environnement pour l'exécution locale des tests
ENV PYTHONPATH=/app
ENV LLM_PROVIDER=openai
ENV OPENAI_API_KEY=fake_key_for_tests

# Exécution des tests unitaires (équivalent de npm test)
# Si cette commande échoue, le processus de build s'arrête net.
RUN pytest tests/ -v


# ---- Étape 2 : Run (Image finale allégée et sécurisée) ----
FROM python:3.10-slim AS run-stage

WORKDIR /app

# Copie du fichier de dépendances original
COPY requirements.txt .

# Exclusion des devDependencies (pytest, httpx) pour la production
# Optimisation de la taille de l'image et réduction de la surface d'attaque
RUN grep -v "^pytest" requirements.txt | grep -v "^httpx" > requirements-prod.txt && \
    pip install --no-cache-dir -r requirements-prod.txt

# Copie uniquement du code source de l'application (pas des tests ni du reste)
COPY ./app ./app

# Exposition du port de l'application
EXPOSE 8000

# Commande de démarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
