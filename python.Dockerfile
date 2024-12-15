FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
RUN pip install --no-cache-dir \
    requests \
    pandas \
    numpy \
    ib_insync

# Ajouter vos scripts
COPY ./scripts /app/scripts

# S'assurer que les scripts sont exécutables
RUN chmod +x /app/scripts/*

# Maintenir le conteneur en vie
CMD ["tail", "-f", "/dev/null"]