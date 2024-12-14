FROM python:3.11-slim

# Installer les dépendances nécessaires
RUN pip install --no-cache-dir requests pandas numpy

# Ajouter vos scripts
WORKDIR /app
COPY ./scripts /app/scripts

# Commande par défaut (modifiée dans docker-compose.yml)
CMD ["python3"]