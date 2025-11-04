#!/usr/bin/env python3
"""
Script para corrigir campos JSON vazios ou malformados na tabela de operadoras
"""

from apps.models.operadora import Operadora
from apps import create_app, db
import sys
import os
import json

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def corrigir_json_operadoras():
    """Corrige campos JSON vazios ou malformados na tabela de operadoras"""

    app = create_app()

    with app.app_context():
        try:
            # Busca todas as operadoras
            operadoras = Operadora.query.all()

            print(f"Verificando {len(operadoras)} operadoras...")

            for operadora in operadoras:
                print(
                    f"Verificando operadora: {operadora.nome} (ID: {operadora.id})")

                # Verifica se configuracao_rpa está vazio ou malformado
                if operadora.configuracao_rpa is None or operadora.configuracao_rpa == "":
                    print(f"  - configuracao_rpa está vazio, definindo como None")
                    operadora.configuracao_rpa = None

                # Se configuracao_rpa é string vazia, converte para None
                elif isinstance(operadora.configuracao_rpa, str) and operadora.configuracao_rpa.strip() == "":
                    print(f"  - configuracao_rpa é string vazia, convertendo para None")
                    operadora.configuracao_rpa = None

                # Se configuracao_rpa é string, tenta fazer parse do JSON
                elif isinstance(operadora.configuracao_rpa, str):
                    try:
                        parsed_json = json.loads(operadora.configuracao_rpa)
                        operadora.configuracao_rpa = parsed_json
                        print(f"  - configuracao_rpa convertido de string para JSON")
                    except json.JSONDecodeError as e:
                        print(
                            f"  - ERRO: configuracao_rpa contém JSON inválido: {e}")
                        print(f"    Valor atual: {operadora.configuracao_rpa}")
                        operadora.configuracao_rpa = None

                # Se já é dict/JSON válido, mantém como está
                elif isinstance(operadora.configuracao_rpa, dict):
                    print(f"  - configuracao_rpa já é JSON válido")

                # Outros tipos, converte para None
                else:
                    print(
                        f"  - configuracao_rpa tem tipo inesperado: {type(operadora.configuracao_rpa)}")
                    operadora.configuracao_rpa = None

            # Commit das mudanças
            db.session.commit()
            print("\n✅ Correção concluída com sucesso!")

        except Exception as e:
            print(f"❌ Erro durante a correção: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    print("🔧 Iniciando correção de campos JSON na tabela de operadoras...")
    corrigir_json_operadoras()
    print("✅ Script concluído!")
