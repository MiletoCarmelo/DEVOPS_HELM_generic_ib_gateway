FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Installer poetry via pip
RUN pip install poetry

# Copier seulement pyproject.toml et poetry.lock (si existe) d'abord
COPY ./python-scripts/pyproject.toml ./python-scripts/poetry.lock* /app/

# Installer les dépendances avec poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Ajouter les scripts
COPY ./python-scripts /app/python-scripts

# S'assurer que les scripts sont exécutables
RUN chmod +x /app/python-scripts/*

# Maintenir le conteneur en vie
CMD ["tail", "-f", "/dev/null"]