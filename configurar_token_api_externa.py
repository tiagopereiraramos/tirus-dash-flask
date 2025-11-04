#!/usr/bin/env python3
"""
Script para configurar token da API externa
Permite configurar o token JWT para autenticação com a API externa
"""

import os
import requests
import json
from datetime import datetime

# Configurações
API_EXTERNA_URL = "http://191.252.218.230:8000"
ENV_FILE = ".env"


def verificar_token_atual():
    """Verifica se já existe um token configurado"""
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r') as f:
            content = f.read()
            if 'API_EXTERNA_TOKEN=' in content:
                print("✅ Token já configurado no arquivo .env")
                return True

    print("⚠️ Nenhum token configurado")
    return False


def obter_token_manual():
    """Permite inserir token manualmente"""
    print("\n🔑 CONFIGURAÇÃO MANUAL DO TOKEN")
    print("=" * 50)
    print("Para obter um token válido:")
    print("1. Acesse a documentação da API: http://191.252.218.230:8000/docs")
    print("2. Faça login ou obtenha um token JWT válido")
    print("3. Cole o token abaixo")
    print("=" * 50)

    token = input("\nDigite o token JWT: ").strip()

    if not token:
        print("❌ Token não fornecido")
        return None

    # Validar token
    print("\n🔍 Validando token...")
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(
            f"{API_EXTERNA_URL}/auth/token", headers=headers, timeout=10)

        if response.status_code == 200:
            print("✅ Token válido!")
            return token
        else:
            print(
                f"❌ Token inválido: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"❌ Erro ao validar token: {e}")
        return None


def salvar_token(token):
    """Salva o token no arquivo .env"""
    print(f"\n💾 Salvando token no arquivo {ENV_FILE}...")

    # Ler arquivo atual se existir
    env_content = ""
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r') as f:
            env_content = f.read()

    # Verificar se já existe configuração de API externa
    lines = env_content.split('\n')
    new_lines = []
    api_config_added = False

    for line in lines:
        if line.startswith('API_EXTERNA_TOKEN='):
            # Atualizar token existente
            new_lines.append(f'API_EXTERNA_TOKEN={token}')
            api_config_added = True
        elif line.startswith('API_EXTERNA_URL='):
            # Manter URL existente
            new_lines.append(line)
            api_config_added = True
        elif line.startswith('API_EXTERNA_USERNAME='):
            # Manter username existente
            new_lines.append(line)
            api_config_added = True
        elif line.startswith('API_EXTERNA_PASSWORD='):
            # Manter password existente
            new_lines.append(line)
            api_config_added = True
        else:
            new_lines.append(line)

    # Adicionar configuração se não existir
    if not api_config_added:
        new_lines.append('')
        new_lines.append('# API Externa Configuration')
        new_lines.append(f'API_EXTERNA_URL={API_EXTERNA_URL}')
        new_lines.append(f'API_EXTERNA_TOKEN={token}')
        new_lines.append('# API_EXTERNA_USERNAME=your_username')
        new_lines.append('# API_EXTERNA_PASSWORD=your_password')

    # Salvar arquivo
    with open(ENV_FILE, 'w') as f:
        f.write('\n'.join(new_lines))

    print("✅ Token salvo com sucesso!")
    print(f"📁 Arquivo: {os.path.abspath(ENV_FILE)}")


def testar_conexao_com_token(token):
    """Testa a conexão usando o token configurado"""
    print(f"\n🧪 Testando conexão com token...")

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    # Testar listagem de jobs
    try:
        response = requests.get(
            f"{API_EXTERNA_URL}/jobs", headers=headers, timeout=10)

        if response.status_code == 200:
            print("✅ Conexão autenticada funcionando!")
            data = response.json()
            print(
                f"📊 Jobs ativos: {len(data) if isinstance(data, list) else 'N/A'}")
            return True
        else:
            print(
                f"❌ Erro na conexão: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Erro ao testar conexão: {e}")
        return False


def main():
    """Função principal"""
    print("🔧 CONFIGURADOR DE TOKEN DA API EXTERNA")
    print("=" * 60)
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"🌐 API URL: {API_EXTERNA_URL}")
    print("=" * 60)

    # Verificar token atual
    if verificar_token_atual():
        resposta = input(
            "\nDeseja reconfigurar o token? (s/N): ").strip().lower()
        if resposta != 's':
            print("✅ Mantendo configuração atual")
            return

    # Obter token
    token = obter_token_manual()

    if not token:
        print("❌ Configuração cancelada")
        return

    # Salvar token
    salvar_token(token)

    # Testar conexão
    if testar_conexao_com_token(token):
        print("\n🎉 Configuração concluída com sucesso!")
        print("💡 O token foi salvo e a conexão está funcionando")
        print("🚀 Agora você pode usar a API externa no sistema")
    else:
        print("\n⚠️ Token salvo, mas conexão falhou")
        print("💡 Verifique se o token está correto e tente novamente")

    print("=" * 60)


if __name__ == "__main__":
    main()
