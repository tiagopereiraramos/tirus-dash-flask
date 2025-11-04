#!/usr/bin/env python3
"""
Script de Teste para Endpoints RPA
Sistema de Orquestração RPA BEG Telecomunicações

Este script testa os endpoints principais do sistema RPA para validar
a integração e funcionamento correto dos payloads e respostas.
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Configurações
BASE_URL = "http://localhost:5050/api/v1"
TEST_TOKEN = None  # Será obtido via login


class RPATester:
    """Classe para testar endpoints RPA"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []

    def login(self, email: str, password: str) -> bool:
        """Realiza login e obtém token JWT"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"email": email, "password": password}
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.session.headers.update({
                        "Authorization": f"Bearer {data['token']}"
                    })
                    print("✅ Login realizado com sucesso")
                    return True
                else:
                    print(f"❌ Erro no login: {data.get('message')}")
                    return False
            else:
                print(f"❌ Erro HTTP {response.status_code} no login")
                return False

        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
            return False

    def test_endpoint(self, method: str, endpoint: str, payload: Optional[Dict] = None,
                      expected_status: int = 200, description: str = "") -> bool:
        """Testa um endpoint específico"""
        try:
            url = f"{self.base_url}{endpoint}"

            print(f"\n🔍 Testando: {description}")
            print(f"   Endpoint: {method} {endpoint}")

            if payload:
                print(f"   Payload: {json.dumps(payload, indent=2)}")

            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=payload)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=payload)
            else:
                print(f"❌ Método {method} não suportado")
                return False

            print(f"   Status: {response.status_code}")

            if response.status_code == expected_status:
                try:
                    data = response.json()
                    print(f"   Resposta: {json.dumps(data, indent=2)}")

                    if data.get("success"):
                        print("✅ Teste PASSED")
                        self.test_results.append({
                            "endpoint": endpoint,
                            "status": "PASSED",
                            "description": description
                        })
                        return True
                    else:
                        print(f"❌ Resposta indica erro: {data.get('message')}")
                        self.test_results.append({
                            "endpoint": endpoint,
                            "status": "FAILED",
                            "description": description,
                            "error": data.get('message')
                        })
                        return False

                except json.JSONDecodeError:
                    print(f"❌ Resposta não é JSON válido: {response.text}")
                    return False
            else:
                print(f"❌ Status code inesperado: {response.status_code}")
                print(f"   Resposta: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Erro no teste: {e}")
            return False

    def test_download_fatura(self) -> bool:
        """Testa endpoint de download de fatura"""
        payload = {
            "processo_id": "550e8400-e29b-41d4-a716-446655440000",
            "operacao": "DOWNLOAD_FATURA",
            "parametros": {
                "cliente": {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "razao_social": "EMPRESA BEG TELECOMUNICAÇÕES LTDA",
                    "nome_sat": "BEG_TELECOM",
                    "cnpj": "12345678000199",
                    "login_portal": "begtelecom@empresa.com",
                    "senha_portal": "senha123",
                    "cpf": "12345678901",
                    "filtro": "fatura_mensal",
                    "unidade": "MATRIZ",
                    "servico": "INTERNET_DEDICADA",
                    "dados_sat": "BEG_TELECOM|INTERNET|DEDICADA"
                },
                "operadora": {
                    "id": "550e8400-e29b-41d4-a716-446655440002",
                    "codigo": "EMB",
                    "nome": "Embratel",
                    "url_portal": "https://portal.embratel.com.br",
                    "classe_rpa": "EmbratelRPA",
                    "configuracao_rpa": {
                        "timeout_padrao": 300,
                        "tentativas_maximas": 3,
                        "parametros_especiais": {
                            "wait_element": 10,
                            "headless": True
                        }
                    }
                },
                "processo": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "mes_ano": "07/2025",
                    "status_atual": "AGUARDANDO_DOWNLOAD"
                },
                "execucao": {
                    "numero_tentativa": 1,
                    "ip_origem": "192.168.1.100",
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            }
        }

        return self.test_endpoint(
            "POST",
            "/rpa/executar-download",
            payload,
            description="Download de Fatura Embratel"
        )

    def test_upload_sat(self) -> bool:
        """Testa endpoint de upload para SAT"""
        payload = {
            "processo_id": "550e8400-e29b-41d4-a716-446655440000",
            "operacao": "UPLOAD_SAT",
            "parametros": {
                "cliente": {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "nome_sat": "BEG_TELECOM",
                    "dados_sat": "BEG_TELECOM|INTERNET|DEDICADA"
                },
                "processo": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "caminho_s3_fatura": "https://minio.local/tirus-faturas/fatura_embratel_07_2025.pdf",
                    "valor_fatura": 1250.50,
                    "data_vencimento": "2025-08-10"
                },
                "sat": {
                    "url_sistema": "https://sat.local/api",
                    "credenciais": {
                        "usuario": "sat_user",
                        "senha": "sat_password"
                    },
                    "configuracao": {
                        "timeout": 300,
                        "retry_attempts": 3
                    }
                }
            }
        }

        return self.test_endpoint(
            "POST",
            "/rpa/executar-upload-sat",
            payload,
            description="Upload para SAT"
        )

    def test_processos_pendentes(self) -> bool:
        """Testa endpoint de listagem de processos pendentes"""
        return self.test_endpoint(
            "GET",
            "/rpa/processos-pendentes?operadora_codigo=EMB&limit=10",
            description="Listagem de Processos Pendentes"
        )

    def test_relatorio_execucoes(self) -> bool:
        """Testa endpoint de relatório de execuções"""
        return self.test_endpoint(
            "GET",
            "/rpa/relatorio-execucoes?data_inicio=2025-07-01&data_fim=2025-07-10&operadora_codigo=EMB",
            description="Relatório de Execuções"
        )

    def test_configurar_operadora(self) -> bool:
        """Testa endpoint de configuração de operadora"""
        payload = {
            "possui_rpa": True,
            "classe_rpa": "EmbratelRPA",
            "configuracao_rpa": {
                "timeout_padrao": 300,
                "tentativas_maximas": 3,
                "parametros_especiais": {
                    "wait_element": 10,
                    "headless": True,
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            }
        }

        return self.test_endpoint(
            "PUT",
            "/operadoras/550e8400-e29b-41d4-a716-446655440002/configurar-rpa",
            payload,
            description="Configuração de Operadora RPA"
        )

    def run_all_tests(self) -> None:
        """Executa todos os testes"""
        print("🚀 Iniciando testes dos endpoints RPA")
        print("=" * 50)

        # Testes principais
        tests = [
            ("Download de Fatura", self.test_download_fatura),
            ("Upload para SAT", self.test_upload_sat),
            ("Processos Pendentes", self.test_processos_pendentes),
            ("Relatório de Execuções", self.test_relatorio_execucoes),
            ("Configurar Operadora", self.test_configurar_operadora)
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            print(f"\n📋 Executando teste: {test_name}")
            if test_func():
                passed += 1
            time.sleep(1)  # Pausa entre testes

        # Relatório final
        print("\n" + "=" * 50)
        print("📊 RELATÓRIO FINAL DOS TESTES")
        print("=" * 50)

        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASSED" else "❌"
            print(
                f"{status_icon} {result['endpoint']} - {result['description']}")
            if result.get("error"):
                print(f"   Erro: {result['error']}")

        print(f"\n📈 Resultado: {passed}/{total} testes PASSED")

        if passed == total:
            print("🎉 Todos os testes PASSED! Sistema RPA funcionando corretamente.")
            return True
        else:
            print("⚠️  Alguns testes FAILED. Verifique os logs acima.")
            return False


def main():
    """Função principal"""
    print("🧪 Teste de Endpoints RPA - BEG Telecomunicações")
    print("=" * 60)

    # Verificar se o servidor está rodando
    try:
        response = requests.get("http://localhost:5050/")
        if response.status_code != 200:
            print("❌ Servidor não está respondendo na porta 5050")
            print("   Execute: uv run python run.py")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Não foi possível conectar ao servidor")
        print("   Verifique se o servidor está rodando na porta 5050")
        sys.exit(1)

    print("✅ Servidor está rodando")

    # Criar tester
    tester = RPATester(BASE_URL)

    # Login (ajuste as credenciais conforme necessário)
    print("\n🔐 Realizando login...")
    if not tester.login("admin@beg.com", "admin123"):
        print("❌ Falha no login. Verifique as credenciais.")
        sys.exit(1)

    # Executar testes
    success = tester.run_all_tests()

    if success:
        print("\n🎯 Todos os endpoints RPA estão funcionando corretamente!")
        print("📋 Documentação completa disponível em: DOCUMENTACAO_RPA_ENDPOINTS.md")
        print("📄 Exemplos de payload em: EXEMPLOS_PAYLOAD_RPA.json")
    else:
        print("\n⚠️  Alguns endpoints precisam de ajustes.")
        print("📋 Consulte a documentação para mais detalhes.")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
