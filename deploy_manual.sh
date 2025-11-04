#!/bin/bash

# Script de Deploy Manual via SSH - BRM Solutions RPA Dashboard
# Uso: ./deploy_manual.sh

set -e

# Configurações
SERVER="191.252.218.230"
USER="root"
PORT="22"
APP_DIR="/opt/brm-rpa-dashboard"

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 Deploy Manual - BRM RPA Dashboard${NC}"
echo "=================================="

# Verificar se o servidor foi configurado
if [ "$SERVER" = "SEU_SERVIDOR_IP" ]; then
    echo -e "${RED}❌ Configure o IP do servidor no script${NC}"
    echo "Edite o arquivo deploy_manual.sh e altere SERVER=\"SEU_SERVIDOR_IP\""
    exit 1
fi

echo -e "${BLUE}📋 Passos para deploy:${NC}"
echo "1. Configure o arquivo .env"
echo "2. Execute: ./deploy_manual.sh"
echo "3. Acesse: http://$SERVER:5050"
echo ""

# Verificar se .env existe
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Arquivo .env não encontrado${NC}"
    echo "Copiando env.sample para .env..."
    cp env.sample .env
    echo -e "${BLUE}⚠️  Configure as variáveis no arquivo .env${NC}"
    exit 1
fi

echo -e "${BLUE}📦 Preparando arquivos...${NC}"

# Criar arquivo tar.gz com os arquivos necessários
TAR_FILE="brm-deploy-$(date +%Y%m%d-%H%M%S).tar.gz"

tar -czf "$TAR_FILE" \
    apps/ \
    nginx/ \
    media/ \
    Dockerfile.prod \
    docker-compose.prod.yml \
    requirements.txt \
    pyproject.toml \
    uv.lock \
    gunicorn-cfg.py \
    run.py \
    .env \
    .gitignore \
    README.md \
    LICENSE.md \
    CHANGELOG.md

echo -e "${BLUE}📤 Enviando arquivos para o servidor...${NC}"
scp -P "$PORT" "$TAR_FILE" "$USER@$SERVER:/tmp/"

echo -e "${BLUE}🔧 Executando deploy no servidor...${NC}"

# Script que será executado no servidor
ssh -p "$PORT" "$USER@$SERVER" << 'EOF'
set -e

APP_DIR="/opt/brm-rpa-dashboard"
TAR_FILE=$(ls /tmp/brm-deploy-*.tar.gz | tail -1)

echo "🚀 Iniciando deploy..."

# Criar diretórios
mkdir -p "$APP_DIR" /opt/backups

# Backup da versão atual
if [ -d "$APP_DIR" ] && [ "$(ls -A "$APP_DIR")" ]; then
    echo "📦 Fazendo backup..."
    BACKUP_NAME="brm-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    tar -czf "/opt/backups/$BACKUP_NAME" -C "$APP_DIR" .
fi

# Parar containers existentes
echo "🛑 Parando containers..."
cd "$APP_DIR" 2>/dev/null || true
docker compose -f docker-compose.prod.yml down --remove-orphans || true

# Limpar e extrair novos arquivos
echo "🧹 Limpando diretório..."
rm -rf "$APP_DIR"/*
cd "$APP_DIR"
tar -xzf "$TAR_FILE"

# Instalar Docker se necessário
if ! command -v docker &> /dev/null; then
    echo "📦 Instalando Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl enable docker
    systemctl start docker
fi

# Instalar docker-compose se necessário
if ! command -v docker compose &> /dev/null; then
    echo "📦 Instalando docker-compose..."
    apt update && apt install -y docker-compose-plugin
fi

# Construir e iniciar
echo "🔨 Construindo containers..."
docker compose -f docker-compose.prod.yml build --no-cache

echo "🚀 Iniciando aplicação..."
docker compose -f docker-compose.prod.yml up -d

# Aguardar e verificar
echo "⏳ Aguardando aplicação..."
sleep 30

if curl -f http://localhost:5050/health >/dev/null 2>&1; then
    echo "✅ Aplicação iniciada com sucesso!"
    echo "🌐 Acesse: http://$(hostname -I | awk '{print $1}'):5050"
else
    echo "❌ Erro ao iniciar aplicação"
    docker compose -f docker-compose.prod.yml logs
    exit 1
fi

# Limpar arquivo temporário
rm -f "$TAR_FILE"

echo "🎉 Deploy concluído!"
EOF

# Limpar arquivo local
rm -f "$TAR_FILE"

echo -e "${GREEN}✅ Deploy concluído com sucesso!${NC}"
echo -e "${BLUE}🌐 Acesse: http://$SERVER:5050${NC}"
echo -e "${BLUE}📊 Logs: ssh $USER@$SERVER 'docker-compose -f $APP_DIR/docker-compose.prod.yml logs -f'${NC}"
