FROM python:3.11-slim

WORKDIR /app

# Forcer IPv4
ENV PYTHONUNBUFFERED=1

# Dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    wget \
    gnupg \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Installer Chrome pour Selenium (méthode moderne)
RUN wget -q -O /tmp/google-chrome-stable_current_amd64.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y /tmp/google-chrome-stable_current_amd64.deb \
    && rm /tmp/google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# Configuration pour préférer IPv4
RUN echo "precedence ::ffff:0:0/96  100" >> /etc/gai.conf

# Copier requirements et installer les dépendances
COPY api/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Télécharger le modèle spaCy français
RUN python -m spacy download fr_core_news_md

# Copier le code de l'API
COPY api/ ./

# Copier le dossier collectors
COPY collectors/ ./collectors/

# Copier le dossier NLP (modules de traitement)
COPY NLP/ ./NLP/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
