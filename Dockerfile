# =========================
# Imagem base
# =========================
FROM ubuntu:22.04

# Define diretório de trabalho
WORKDIR /app

# =========================
# Dependências do sistema
# =========================
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    curl \
    gnupg \
    lsb-release \
    unzip \
    git \
    unixodbc-dev \
 && rm -rf /var/lib/apt/lists/*

# =========================
# Instala ODBC Microsoft
# =========================
RUN curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list -o /etc/apt/sources.list.d/mssql-release.list \
 && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/trusted.gpg.d/microsoft.gpg \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
 && rm -rf /var/lib/apt/lists/*

# =========================
# Instala Ollama CLI
# =========================
RUN curl -fsSL https://ollama.com/install.sh | bash

# Baixa modelo TinyLlama (opcional, mas garante que o container já tenha)
RUN ollama pull TinyLlama

# =========================
# Instala dependências Python
# =========================
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# =========================
# Copia código da aplicação
# =========================
COPY . .

# =========================
# Comando padrão
# =========================
CMD ["python3", "main.py"]
