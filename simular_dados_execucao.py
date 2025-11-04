#!/usr/bin/env python3
"""
Script para simular dados de execução da API externa
Permite testar a interface sem depender dos RPAs reais
"""

from apps.models.execucao import TipoExecucao, StatusExecucao
from apps.models import Processo, Execucao, Cliente, Operadora
from apps import create_app, db
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Adicionar o diretório do projeto ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
logger = logging.getLogger(__name__)


class SimuladorDadosExecucao:
    """Simula dados de execução da API externa"""

    def __init__(self):
        self.app = create_app()

    def criar_payload_sucesso(self, processo: Processo) -> Dict[str, Any]:
        """Cria payload de sucesso baseado no exemplo fornecido"""
        hash_execucao = f"{processo.cliente.operadora.codigo}-{processo.cliente.cnpj.replace('.', '').replace('/', '').replace('-', '')}-DOWNLOAD-{processo.mes_ano.replace('/', '-')}"

        return {
            "success": True,
            "message": f"Processo concluído com 12 faturas e 12 comprovantes enviados ao SAT.",
            "processes": [
                {
                    "hash_execucao": hash_execucao,
                    "status_final": "UPLOADED_SAT",
                    "cliente": processo.cliente.razao_social,
                    "operadora": processo.cliente.operadora.codigo,
                    "servico": "DOWNLOAD_FATURAS",
                    "criado_em": datetime.now().isoformat() + "Z",
                    "finalizado_em": (datetime.now() + timedelta(minutes=3)).isoformat() + "Z",
                    "faturas": [
                        {
                            "caminho": f"s3://brm-bucket/{processo.cliente.operadora.codigo}/2025-10/0001.pdf",
                            "data_vencimento": "20-10-2025",
                            "mes": 10,
                            "ano": 2025
                        }
                    ],
                    "metricas": {
                        "tempo_execucao_segundos": 187,
                        "requisicoes_http": 36,
                        "erros_recuperados": 0
                    }
                }
            ],
            "timestamp": (datetime.now() + timedelta(minutes=3)).isoformat() + "Z"
        }

    def criar_payload_erro(self, processo: Processo) -> Dict[str, Any]:
        """Cria payload de erro baseado no exemplo fornecido"""
        hash_execucao = f"{processo.cliente.operadora.codigo}-{processo.cliente.cnpj.replace('.', '').replace('/', '').replace('-', '')}-UPLOAD-{processo.mes_ano.replace('/', '-')}"

        return {
            "success": False,
            "message": "Processo interrompido: falha crítica na etapa de autenticação.",
            "processes": [
                {
                    "hash_execucao": hash_execucao,
                    "status_final": "FAILED",
                    "cliente": processo.cliente.razao_social,
                    "operadora": processo.cliente.operadora.codigo,
                    "servico": "UPLOAD_SAT",
                    "criado_em": datetime.now().isoformat() + "Z",
                    "finalizado_em": (datetime.now() + timedelta(minutes=2)).isoformat() + "Z",
                    "detalhes": {
                        "etapa_falha": "LOGIN_PORTAL",
                        "codigo_erro": "AUTH-401",
                        "mensagem_erro": "Credenciais inválidas ou sessão expirada.",
                        "tentativas": 3,
                        "acao_recomendada": f"Atualizar senha no portal {processo.cliente.operadora.codigo} e reenfileirar."
                    }
                }
            ],
            "timestamp": (datetime.now() + timedelta(minutes=2)).isoformat() + "Z"
        }

    def simular_execucao_sucesso(self, processo_id: int) -> bool:
        """Simula uma execução com sucesso"""
        with self.app.app_context():
            try:
                processo = Processo.query.get(processo_id)
                if not processo:
                    logger.error(f"Processo {processo_id} não encontrado")
                    return False

                # Criar execução
                execucao = Execucao(
                    processo_id=processo.id,
                    tipo_execucao=TipoExecucao.DOWNLOAD_FATURA.value,
                    status_execucao=StatusExecucao.EXECUTANDO.value,
                    classe_rpa_utilizada="API_EXTERNA_SIMULADA",
                    parametros_entrada={
                        "operadora": processo.cliente.operadora.codigo,
                        "cliente": processo.cliente.razao_social,
                        "cnpj": processo.cliente.cnpj,
                        "filtro": processo.cliente.filtro,
                        "simulado": True
                    },
                    numero_tentativa=1,
                    ip_origem="127.0.0.1",
                    user_agent="Simulador Dados Execução"
                )

                db.session.add(execucao)
                db.session.commit()

                # Simular payload de sucesso
                payload_sucesso = self.criar_payload_sucesso(processo)

                # Atualizar execução com sucesso
                execucao.finalizar_com_sucesso(
                    resultado=payload_sucesso,
                    mensagem="Execução simulada concluída com sucesso"
                )

                # Atualizar processo
                processo.status_processo = "DOWNLOAD_CONCLUIDO"
                processo.url_fatura = payload_sucesso["processes"][0]["faturas"][0]["caminho"]
                processo.caminho_s3_fatura = payload_sucesso["processes"][0]["faturas"][0]["caminho"]

                # Adicionar dados realistas da fatura
                import random
                processo.valor_fatura = round(
                    random.uniform(150.00, 2500.00), 2)
                processo.data_vencimento = datetime.now() + timedelta(days=random.randint(5, 15))

                db.session.commit()

                logger.info(
                    f"✅ Execução simulada com sucesso para processo {processo_id}")
                print(
                    f"✅ Processo {processo_id} - {processo.cliente.razao_social}")
                print(f"   Status: {processo.status_processo}")
                print(f"   URL Fatura: {processo.url_fatura}")
                print(
                    f"   Hash Execução: {payload_sucesso['processes'][0]['hash_execucao']}")

                return True

            except Exception as e:
                logger.error(f"Erro ao simular execução de sucesso: {str(e)}")
                db.session.rollback()
                return False

    def simular_execucao_erro(self, processo_id: int) -> bool:
        """Simula uma execução com erro"""
        with self.app.app_context():
            try:
                processo = Processo.query.get(processo_id)
                if not processo:
                    logger.error(f"Processo {processo_id} não encontrado")
                    return False

                # Criar execução
                execucao = Execucao(
                    processo_id=processo.id,
                    tipo_execucao=TipoExecucao.DOWNLOAD_FATURA.value,
                    status_execucao=StatusExecucao.EXECUTANDO.value,
                    classe_rpa_utilizada="API_EXTERNA_SIMULADA",
                    parametros_entrada={
                        "operadora": processo.cliente.operadora.codigo,
                        "cliente": processo.cliente.razao_social,
                        "cnpj": processo.cliente.cnpj,
                        "filtro": processo.cliente.filtro,
                        "simulado": True
                    },
                    numero_tentativa=1,
                    ip_origem="127.0.0.1",
                    user_agent="Simulador Dados Execução"
                )

                db.session.add(execucao)
                db.session.commit()

                # Simular payload de erro
                payload_erro = self.criar_payload_erro(processo)

                # Atualizar execução com erro
                execucao.finalizar_com_erro(
                    Exception(payload_erro["message"]),
                    payload_erro
                )

                # Atualizar processo
                processo.status_processo = "ERRO_DOWNLOAD"

                db.session.commit()

                logger.info(
                    f"❌ Execução simulada com erro para processo {processo_id}")
                print(
                    f"❌ Processo {processo_id} - {processo.cliente.razao_social}")
                print(f"   Status: {processo.status_processo}")
                print(f"   Erro: {payload_erro['message']}")
                print(
                    f"   Hash Execução: {payload_erro['processes'][0]['hash_execucao']}")

                return True

            except Exception as e:
                logger.error(f"Erro ao simular execução com erro: {str(e)}")
                db.session.rollback()
                return False

    def listar_processos_disponiveis(self) -> List[Dict[str, Any]]:
        """Lista processos disponíveis para simulação"""
        with self.app.app_context():
            processos = Processo.query.join(Cliente).join(Operadora).all()

            print("\n📋 PROCESSOS DISPONÍVEIS PARA SIMULAÇÃO:")
            print("=" * 60)

            for i, processo in enumerate(processos, 1):
                print(
                    f"{i:2d}. ID: {str(processo.id)[:8]}... | {processo.cliente.razao_social[:30]:30s} | {processo.cliente.operadora.nome:12s} | {processo.status_processo}")

            return [
                {
                    "id": p.id,
                    "cliente": p.cliente.razao_social,
                    "operadora": p.cliente.operadora.nome,
                    "status": p.status_processo
                }
                for p in processos
            ]

    def menu_interativo(self):
        """Menu interativo para simulação"""
        while True:
            print("\n" + "="*60)
            print("🎭 SIMULADOR DE DADOS DE EXECUÇÃO")
            print("="*60)
            print("1. Listar processos disponíveis")
            print("2. Simular execução com SUCESSO")
            print("3. Simular execução com ERRO")
            print("4. Simular múltiplas execuções")
            print("0. Sair")
            print("-"*60)

            opcao = input("Escolha uma opção: ").strip()

            if opcao == "0":
                print("👋 Saindo do simulador...")
                break
            elif opcao == "1":
                self.listar_processos_disponiveis()
            elif opcao == "2":
                processo_id = input(
                    "Digite o ID do processo para simular SUCESSO: ").strip()
                try:
                    processo_id = int(processo_id)
                    self.simular_execucao_sucesso(processo_id)
                except ValueError:
                    print("❌ ID inválido")
            elif opcao == "3":
                processo_id = input(
                    "Digite o ID do processo para simular ERRO: ").strip()
                try:
                    processo_id = int(processo_id)
                    self.simular_execucao_erro(processo_id)
                except ValueError:
                    print("❌ ID inválido")
            elif opcao == "4":
                self.simular_multiplas_execucoes()
            else:
                print("❌ Opção inválida")

    def simular_multiplas_execucoes(self):
        """Simula múltiplas execuções para teste"""
        print("\n🎲 SIMULAÇÃO MÚLTIPLA")
        print("-" * 30)

        with self.app.app_context():
            processos = Processo.query.limit(5).all()

            for i, processo in enumerate(processos):
                if i % 2 == 0:
                    # Simular sucesso
                    self.simular_execucao_sucesso(processo.id)
                else:
                    # Simular erro
                    self.simular_execucao_erro(processo.id)

                print()  # Linha em branco entre execuções


def main():
    """Função principal"""
    print("🎭 SIMULADOR DE DADOS DE EXECUÇÃO")
    print("=" * 50)
    print("Este script simula dados de execução da API externa")
    print("para permitir testes da interface sem depender dos RPAs reais.")
    print()

    simulador = SimuladorDadosExecucao()

    # Verificar se há argumentos de linha de comando
    if len(sys.argv) > 1:
        comando = sys.argv[1].lower()

        if comando == "listar":
            simulador.listar_processos_disponiveis()
        elif comando == "sucesso" and len(sys.argv) > 2:
            processo_id = sys.argv[2]
            simulador.simular_execucao_sucesso(processo_id)
        elif comando == "erro" and len(sys.argv) > 2:
            processo_id = sys.argv[2]
            simulador.simular_execucao_erro(processo_id)
        elif comando == "multiplas":
            simulador.simular_multiplas_execucoes()
        else:
            print("❌ Comando inválido")
            print(
                "Uso: python simular_dados_execucao.py [listar|sucesso ID|erro ID|multiplas]")
    else:
        # Modo interativo
        simulador.menu_interativo()


if __name__ == "__main__":
    main()
