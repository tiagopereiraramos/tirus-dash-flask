#!/bin/bash

# Script de Deploy via SSH - BRM Solutions RPA Dashboard
# Uso: ./deploy_ssh.sh [servidor] [porta] [usuario]

set -e  # Parar em caso de erro

# Configurações padrão
DEFAULT_SERVER="seu-servidor.com"
DEFAULT_PORT="22"
DEFAULT_USER="root"
DEFAULT_APP_DIR="/opt/brm-rpa-dashboard"
DEFAULT_BACKUP_DIR="/opt/backups"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para imprimir com cores
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar argumentos
SERVER=${1:-$DEFAULT_SERVER}
PORT=${2:-$DEFAULT_PORT}
USER=${3:-$DEFAULT_USER}

# Verificar se o servidor foi especificado
if [ "$SERVER" = "$DEFAULT_SERVER" ]; then
    print_error "Por favor, especifique o servidor:"
    echo "Uso: $0 <servidor> [porta] [usuario]"
    echo "Exemplo: $0 192.168.1.100 22 root"
    exit 1
fi

print_status "🚀 Iniciando deploy para $USER@$SERVER:$PORT"

# Verificar se estamos no diretório correto
if [ ! -f "Dockerfile.prod" ] || [ ! -f "docker-compose.prod.yml" ]; then
    print_error "Execute este script no diretório raiz do projeto"
    exit 1
fi

# Verificar se git está limpo
if [ -n "$(git status --porcelain)" ]; then
    print_warning "Há mudanças não commitadas no git"
    read -p "Continuar mesmo assim? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Criar arquivo .env se não existir
if [ ! -f ".env" ]; then
    print_status "Criando arquivo .env..."
    cp env.sample .env
    print_warning "Configure as variáveis no arquivo .env antes do deploy"
fi

# Verificar se Docker está instalado localmente
if ! command -v docker &> /dev/null; then
    print_error "Docker não está instalado localmente"
    exit 1
fi

# Verificar se docker-compose está disponível
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose não está disponível"
    exit 1
fi

print_status "📦 Preparando arquivos para deploy..."

# Criar diretório temporário para deploy
TEMP_DIR=$(mktemp -d)
print_status "Diretório temporário: $TEMP_DIR"

# Copiar arquivos necessários
print_status "Copiando arquivos..."
cp -r apps/ "$TEMP_DIR/"
cp -r nginx/ "$TEMP_DIR/"
cp -r media/ "$TEMP_DIR/"
cp Dockerfile.prod "$TEMP_DIR/"
cp docker-compose.prod.yml "$TEMP_DIR/"
cp requirements.txt "$TEMP_DIR/"
cp pyproject.toml "$TEMP_DIR/"
cp uv.lock "$TEMP_DIR/"
cp gunicorn-cfg.py "$TEMP_DIR/"
cp run.py "$TEMP_DIR/"
cp .env "$TEMP_DIR/"
cp .gitignore "$TEMP_DIR/"

# Criar script de deploy no servidor
cat > "$TEMP_DIR/deploy_server.sh" << 'EOF'
#!/bin/bash

set -e

# Configurações
APP_DIR="/opt/brm-rpa-dashboard"
BACKUP_DIR="/opt/backups"
LOG_FILE="/var/log/brm-deploy.log"

# Funções
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Criar diretórios se não existirem
mkdir -p "$APP_DIR" "$BACKUP_DIR" /var/log

log "🚀 Iniciando deploy..."

# Fazer backup da versão atual se existir
if [ -d "$APP_DIR" ] && [ "$(ls -A "$APP_DIR")" ]; then
    log "📦 Fazendo backup da versão atual..."
    BACKUP_NAME="brm-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    tar -czf "$BACKUP_DIR/$BACKUP_NAME" -C "$APP_DIR" .
    log "Backup salvo em: $BACKUP_DIR/$BACKUP_NAME"
fi

# Parar containers existentes
log "🛑 Parando containers existentes..."
cd "$APP_DIR" 2>/dev/null || true
docker-compose -f docker-compose.prod.yml down --remove-orphans || true

# Limpar diretório da aplicação
log "🧹 Limpando diretório da aplicação..."
rm -rf "$APP_DIR"/*

# Copiar novos arquivos
log "📋 Copiando novos arquivos..."
cp -r ./* "$APP_DIR/"

# Ir para diretório da aplicação
cd "$APP_DIR"

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    log "📦 Instalando Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl enable docker
    systemctl start docker
fi

# Verificar se docker-compose está instalado
if ! command -v docker-compose &> /dev/null; then
    log "📦 Instalando docker-compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Construir e iniciar containers
log "🔨 Construindo containers..."
docker-compose -f docker-compose.prod.yml build --no-cache

log "🚀 Iniciando aplicação..."
docker-compose -f docker-compose.prod.yml up -d

# Aguardar aplicação estar pronta
log "⏳ Aguardando aplicação estar pronta..."
sleep 30

# Verificar se aplicação está rodando
if curl -f http://localhost:5050/health >/dev/null 2>&1; then
    log "✅ Aplicação iniciada com sucesso!"
    log "🌐 Acesse: http://$(hostname -I | awk '{print $1}'):5050"
else
    log "❌ Erro ao iniciar aplicação"
    docker-compose -f docker-compose.prod.yml logs
    exit 1
fi

log "🎉 Deploy concluído com sucesso!"
EOF

chmod +x "$TEMP_DIR/deploy_server.sh"

# Transferir arquivos para o servidor
print_status "📤 Transferindo arquivos para o servidor..."
rsync -avz -e "ssh -p $PORT" "$TEMP_DIR/" "$USER@$SERVER:/tmp/brm-deploy/"

# Executar deploy no servidor
print_status "🔧 Executando deploy no servidor..."
ssh -p "$PORT" "$USER@$SERVER" "chmod +x /tmp/brm-deploy/deploy_server.sh && /tmp/brm-deploy/deploy_server.sh"

# Limpar arquivos temporários
print_status "🧹 Limpando arquivos temporários..."
rm -rf "$TEMP_DIR"

print_success "🎉 Deploy concluído com sucesso!"
print_status "🌐 Acesse: http://$SERVER:5050"
print_status "📊 Logs: ssh $USER@$SERVER 'docker-compose -f $DEFAULT_APP_DIR/docker-compose.prod.yml logs -f'"
