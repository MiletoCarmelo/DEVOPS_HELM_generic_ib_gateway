#!/bin/bash

# Couleurs et styles
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Variables
NAMESPACE="trading"
SECRET_NAME="ib-gateway-secrets" # Doit correspondre à .Values.secret.name dans values.yaml
ENV_FILE=".env"

# Fonction pour afficher les messages
log() {
    local level=$1
    local message=$2
    case $level in
        "info")
            echo -e "${BLUE}ℹ️ ${message}${NC}"
            ;;
        "success")
            echo -e "${GREEN}✅ ${message}${NC}"
            ;;
        "error")
            echo -e "${RED}❌ ${message}${NC}"
            ;;
        "warning")
            echo -e "${YELLOW}⚠️ ${message}${NC}"
            ;;
    esac
}

# Vérification de l'existence du fichier .env
if [ ! -f "$ENV_FILE" ]; then
    log "error" "Le fichier $ENV_FILE n'existe pas"
    echo "Créez un fichier $ENV_FILE avec les variables suivantes:"
    echo "TWS_USERID=votre_username"
    echo "TWS_PASSWORD=votre_password"
    echo "IB_ACCOUNT=votre_compte"
    exit 1
fi

# Vérification de kubectl
if ! command -v kubectl &> /dev/null; then
    log "error" "kubectl n'est pas installé"
    exit 1
fi

# Lecture des variables sensibles depuis le fichier .env
log "info" "Lecture des variables depuis $ENV_FILE..."
TWS_USERID=$(grep TWS_USERID "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'" | xargs)
TWS_PASSWORD=$(grep TWS_PASSWORD "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'" | xargs)
IB_ACCOUNT=$(grep IB_ACCOUNT "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'" | xargs)

# Vérification des variables requises
missing_vars=()
[ -z "$TWS_USERID" ] && missing_vars+=("TWS_USERID")
[ -z "$TWS_PASSWORD" ] && missing_vars+=("TWS_PASSWORD")
[ -z "$IB_ACCOUNT" ] && missing_vars+=("IB_ACCOUNT")

if [ ${#missing_vars[@]} -ne 0 ]; then
    log "error" "Variables manquantes dans $ENV_FILE:"
    for var in "${missing_vars[@]}"; do
        echo "- $var"
    done
    exit 1
fi

# Vérification de la connexion au cluster
log "info" "Vérification de la connexion au cluster Kubernetes..."
if ! kubectl cluster-info &> /dev/null; then
    log "error" "Impossible de se connecter au cluster Kubernetes"
    exit 1
fi

# Création du namespace s'il n'existe pas
log "info" "Création du namespace ${NAMESPACE}..."
if kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f - ; then
    log "success" "Namespace ${NAMESPACE} prêt"
else
    log "error" "Erreur lors de la création du namespace"
    exit 1
fi

# Création du secret pour IB Gateway
log "info" "Création du secret ${SECRET_NAME}..."
if kubectl create secret generic "${SECRET_NAME}" \
    -n "${NAMESPACE}" \
    --from-literal=TWS_USERID="${TWS_USERID}" \
    --from-literal=TWS_PASSWORD="${TWS_PASSWORD}" \
    --from-literal=IB_ACCOUNT="${IB_ACCOUNT}" \
    --dry-run=client -o yaml | kubectl apply -f - ; then
    log "success" "Secret ${SECRET_NAME} créé avec succès"
else
    log "error" "Erreur lors de la création du secret"
    exit 1
fi

# Vérification du secret
log "info" "Vérification du secret..."
if kubectl get secret "${SECRET_NAME}" -n "${NAMESPACE}" &> /dev/null; then
    log "success" "Le secret ${SECRET_NAME} existe dans le namespace ${NAMESPACE}"
else
    log "error" "Le secret ${SECRET_NAME} n'a pas été créé correctement"
    exit 1
fi

# Affichage du résumé
echo -e "\n${BOLD}Résumé de l'installation :${NC}"
echo -e "Namespace: ${BLUE}${NAMESPACE}${NC}"
echo -e "Secret: ${BLUE}${SECRET_NAME}${NC}"
echo -e "Username configuré: ${BLUE}${TWS_USERID}${NC}"
echo -e "Compte IB configuré: ${BLUE}${IB_ACCOUNT}${NC}"

log "success" "Configuration terminée avec succès !"