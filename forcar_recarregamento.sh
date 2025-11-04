#!/bin/bash

echo "🚀 Forçando recarregamento completo..."

# Parar servidor
echo "📋 Parando servidor..."
pkill -f "python run.py" 2>/dev/null || echo "Servidor não estava rodando"

# Aguardar um pouco
sleep 2

# Verificar se a porta está livre
if lsof -ti:5050 > /dev/null 2>&1; then
    echo "🔴 Porta 5050 ainda em uso, forçando liberação..."
    lsof -ti:5050 | xargs kill -9
    sleep 1
fi

# Limpar cache Python
echo "🐍 Limpando cache Python..."
find . -name "*.pyc" -delete 2>/dev/null
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Limpar cache Flask
echo "🔥 Limpando cache Flask..."
rm -rf instance/ 2>/dev/null

# Verificar mudanças no CSS
echo "🎨 Verificando mudanças no CSS..."
echo "Versão atual: v=20250118d"
grep -n "#1a2634" apps/static/assets/css/dark.css

echo ""
echo "✅ Servidor pronto para reiniciar!"
echo "💡 Agora faça:"
echo "   1. Cmd + Shift + R no navegador"
echo "   2. Ou F12 → botão direito no recarregar → 'Empty Cache and Hard Reload'"
echo "   3. Ou abra uma aba anônima"
echo ""

# Iniciar servidor
echo "🚀 Iniciando servidor..."
python run.py
