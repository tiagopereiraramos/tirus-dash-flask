#!/usr/bin/env python3
"""
Script de teste para integração com RPA terceirizada
Demonstra como usar as novas funcionalidades do sistema
"""

import requests
import json
import sys
from datetime import datetime

# Configurações
BASE_URL = "http://localhost:5050"
ENDPOINT_RPA_TESTE = "https://httpbin.org/post"  # Endpoint de teste


def testar_conexao_rpa():
    """Testa a conexão com RPA terceirizada"""
    print("🔌 Testando conexão com RPA terceirizada...")

    url = f"{BASE_URL}/processos/teste-rpa-terceirizada"
    payload = {
        "url_endpoint": ENDPOINT_RPA_TESTE
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()

        if data.get('success'):
            print("✅ Conexão estabelecida com sucesso!")
            print(
                f"📋 Resposta: {json.dumps(data.get('response', {}), indent=2)}")
        else:
            print(f"❌ Erro na conexão: {data.get('message')}")

    except Exception as e:
        print(f"❌ Erro ao testar conexão: {str(e)}")


def obter_payload_processo(processo_id):
    """Obtém o payload de um processo específico"""
    print(f"📦 Obtendo payload do processo {processo_id}...")

    url = f"{BASE_URL}/processos/payload-processo/{processo_id}"

    try:
        response = requests.get(url)
        data = response.json()

        if data.get('success'):
            print("✅ Payload obtido com sucesso!")
            print(
                f"📋 Payload: {json.dumps(data.get('payload', {}), indent=2)}")
            return data.get('payload')
        else:
            print(f"❌ Erro ao obter payload: {data.get('message')}")
            return None

    except Exception as e:
        print(f"❌ Erro ao obter payload: {str(e)}")
        return None


def listar_execucoes_processo(processo_id):
    """Lista as execuções de um processo"""
    print(f"📊 Listando execuções do processo {processo_id}...")

    url = f"{BASE_URL}/processos/execucoes/{processo_id}"

    try:
        response = requests.get(url)
        data = response.json()

        if data.get('success'):
            execucoes = data.get('execucoes', [])
            print(f"✅ Encontradas {len(execucoes)} execuções:")

            for i, execucao in enumerate(execucoes, 1):
                print(
                    f"  {i}. {execucao.get('tipo_execucao')} - {execucao.get('status_execucao')}")
                print(f"     Data: {execucao.get('data_inicio')}")
                print(
                    f"     RPA: {execucao.get('classe_rpa_utilizada', 'N/A')}")
                if execucao.get('duracao_segundos'):
                    print(f"     Duração: {execucao.get('duracao_segundos')}s")
                print()
        else:
            print(f"❌ Erro ao listar execuções: {data.get('message')}")

    except Exception as e:
        print(f"❌ Erro ao listar execuções: {str(e)}")


def enviar_processo_rpa(processo_id, url_endpoint):
    """Envia um processo para execução RPA terceirizada"""
    print(f"🚀 Enviando processo {processo_id} para RPA terceirizada...")

    url = f"{BASE_URL}/processos/enviar-rpa-terceirizada/{processo_id}"
    payload = {
        "url_endpoint": url_endpoint
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()

        if data.get('success'):
            print("✅ Processo enviado com sucesso!")
            print(f"📋 Execução ID: {data.get('execucao_id')}")
            if data.get('resultado'):
                print(
                    f"📋 Resultado: {json.dumps(data.get('resultado'), indent=2)}")
        else:
            print(f"❌ Erro ao enviar processo: {data.get('message')}")

    except Exception as e:
        print(f"❌ Erro ao enviar processo: {str(e)}")


def demonstrar_fluxo_completo():
    """Demonstra o fluxo completo de integração"""
    print("🔄 Demonstrando fluxo completo de integração RPA...")
    print("=" * 60)

    # 1. Testar conexão
    testar_conexao_rpa()
    print()

    # 2. Obter payload de exemplo (usando um ID fictício)
    processo_id_exemplo = "32a1fb27-9b53-4053-b69d-99200782a942"
    payload = obter_payload_processo(processo_id_exemplo)
    print()

    # 3. Listar execuções
    listar_execucoes_processo(processo_id_exemplo)
    print()

    # 4. Enviar para RPA (apenas simulação)
    print("⚠️  Nota: Envio real para RPA requer endpoint válido")
    print("   Para testar com endpoint real, use:")
    print(
        f"   enviar_processo_rpa('{processo_id_exemplo}', 'https://seu-endpoint-rpa.com/api')")


def mostrar_ajuda():
    """Mostra ajuda sobre como usar o script"""
    print("""
🔧 Script de Teste - Integração RPA Terceirizada

Uso:
    python test_integracao_rpa.py [comando] [parâmetros]

Comandos disponíveis:
    testar_conexao          - Testa conexão com RPA terceirizada
    obter_payload <id>      - Obtém payload de um processo
    listar_execucoes <id>   - Lista execuções de um processo
    enviar_rpa <id> <url>   - Envia processo para RPA terceirizada
    demo                    - Executa demonstração completa
    ajuda                   - Mostra esta ajuda

Exemplos:
    python test_integracao_rpa.py testar_conexao
    python test_integracao_rpa.py obter_payload 32a1fb27-9b53-4053-b69d-99200782a942
    python test_integracao_rpa.py listar_execucoes 32a1fb27-9b53-4053-b69d-99200782a942
    python test_integracao_rpa.py demo
    """)


def main():
    """Função principal"""
    if len(sys.argv) < 2:
        mostrar_ajuda()
        return

    comando = sys.argv[1].lower()

    if comando == "testar_conexao":
        testar_conexao_rpa()

    elif comando == "obter_payload":
        if len(sys.argv) < 3:
            print("❌ ID do processo é obrigatório")
            return
        obter_payload_processo(sys.argv[2])

    elif comando == "listar_execucoes":
        if len(sys.argv) < 3:
            print("❌ ID do processo é obrigatório")
            return
        listar_execucoes_processo(sys.argv[2])

    elif comando == "enviar_rpa":
        if len(sys.argv) < 4:
            print("❌ ID do processo e URL do endpoint são obrigatórios")
            return
        enviar_processo_rpa(sys.argv[2], sys.argv[3])

    elif comando == "demo":
        demonstrar_fluxo_completo()

    elif comando == "ajuda":
        mostrar_ajuda()

    else:
        print(f"❌ Comando desconhecido: {comando}")
        mostrar_ajuda()


if __name__ == "__main__":
    main()
