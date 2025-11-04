#!/bin/bash

echo "🚀 Build para Easy Panel - BRM RPA Dashboard"

# Verificar se estamos no diretório correto
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Erro: pyproject.toml não encontrado. Execute este script no diretório raiz do projeto."
    exit 1
fi

# Verificar se o Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo "❌ Erro: Docker não está rodando."
    exit 1
fi

echo "📋 Verificando arquivos necessários..."

# Verificar arquivos essenciais
required_files=(
    "Dockerfile.easypanel"
    "docker-compose.traefik.yml"
    "easypanel.json"
    "pyproject.toml"
    "uv.lock"
    "apps/__init__.py"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Arquivo não encontrado: $file"
        exit 1
    fi
done

echo "✅ Todos os arquivos necessários encontrados"

# Build da imagem
echo "🔨 Fazendo build da imagem Docker..."
docker build -f Dockerfile.easypanel -t brm-rpa-dashboard:latest .

if [ $? -eq 0 ]; then
    echo "✅ Build concluído com sucesso!"

    # Mostrar informações da imagem
    echo "📊 Informações da imagem:"
    docker images brm-rpa-dashboard:latest

    echo ""
    echo "🎯 Próximos passos:"
    echo "1. Copie os arquivos para o servidor:"
    echo "   - Dockerfile.easypanel"
    echo "   - docker-compose.traefik.yml"
    echo "   - easypanel.json"
    echo "   - pyproject.toml"
    echo "   - uv.lock"
    echo "   - apps/ (diretório completo)"
    echo ""
    echo "2. No Easy Panel:"
    echo "   - Crie um novo projeto"
    echo "   - Use o docker-compose.traefik.yml"
    echo "   - Configure o domínio"
    echo "   - Deploy!"
    echo ""
    echo "3. Verifique o health check:"
    echo "   curl https://seu-dominio.com/health"

else
    echo "❌ Erro no build da imagem"
    exit 1
fi
