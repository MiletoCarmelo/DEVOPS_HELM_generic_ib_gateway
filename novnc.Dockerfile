FROM debian:bullseye-slim

# Installation des dépendances
RUN apt-get update && apt-get install -y \
    git \
    procps \ 
    python3 \
    python3-numpy \
    && rm -rf /var/lib/apt/lists/*

# Installation de noVNC
RUN git clone https://github.com/novnc/noVNC.git /opt/novnc && \
    git clone https://github.com/novnc/websockify /opt/novnc/utils/websockify

# Configuration
EXPOSE 6080
ENV DISPLAY_WIDTH=1280
ENV DISPLAY_HEIGHT=720

# Script de démarrage
COPY /scripts/novnc-start.sh /scripts/novnc-start.sh
RUN chmod +x /scripts/novnc-start.sh

CMD ["/scripts/novnc-start.sh"]