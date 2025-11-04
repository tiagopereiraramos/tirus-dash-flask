#!/usr/bin/env python3
"""
Script para criar agendamentos específicos por operadora
"""

from apps.models import Agendamento, TipoAgendamento, Operadora
from apps import create_app, db
import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def criar_agendamentos_por_operadora():
    """Cria agendamentos específicos para cada operadora"""

    app = create_app()

    with app.app_context():
        try:
            print("🔄 Criando agendamentos específicos por operadora...")

            # Buscar operadoras ativas
            operadoras = Operadora.query.filter_by(status_ativo=True).all()

            if not operadoras:
                print("⚠️  Nenhuma operadora ativa encontrada")
                return False

            print(f"📋 Encontradas {len(operadoras)} operadoras ativas")

            agendamentos_criados = 0

            for operadora in operadoras:
                print(
                    f"\n🏢 Processando operadora: {operadora.nome} ({operadora.codigo})")

                # 1. Agendamento de downloads específico da operadora
                nome_download = f"Downloads {operadora.nome}"
                agendamento_existente = Agendamento.query.filter_by(
                    nome_agendamento=nome_download
                ).first()

                if not agendamento_existente:
                    agendamento_download = Agendamento(
                        nome_agendamento=nome_download,
                        descricao=f"Downloads automáticos de faturas da {operadora.nome}",
                        cron_expressao="0 9 * * 1-5",  # Segunda a sexta às 09:00
                        tipo_agendamento=TipoAgendamento.EXECUTAR_DOWNLOADS.value,
                        operadora_id=operadora.id,
                        parametros_execucao={
                            "apenas_processos_pendentes": True,
                            "limite_execucoes_simultaneas": 3,
                            "operadora_especifica": operadora.codigo
                        }
                    )
                    db.session.add(agendamento_download)
                    print(
                        f"  ✅ Agendamento de downloads criado para {operadora.nome}")
                    agendamentos_criados += 1
                else:
                    print(
                        f"  ⚠️  Agendamento de downloads já existe para {operadora.nome}")

                # 2. Agendamento de relatórios específico da operadora
                nome_relatorio = f"Relatório {operadora.nome}"
                agendamento_existente = Agendamento.query.filter_by(
                    nome_agendamento=nome_relatorio
                ).first()

                if not agendamento_existente:
                    agendamento_relatorio = Agendamento(
                        nome_agendamento=nome_relatorio,
                        descricao=f"Relatório semanal de atividades da {operadora.nome}",
                        cron_expressao="0 16 * * 5",  # Toda sexta às 16:00
                        tipo_agendamento=TipoAgendamento.ENVIAR_RELATORIOS.value,
                        operadora_id=operadora.id,
                        parametros_execucao={
                            "tipo_relatorio": "semanal",
                            "incluir_graficos": True,
                            "operadora_especifica": operadora.codigo,
                            "destinatarios": ["admin@begtelecomunicacoes.com.br"]
                        }
                    )
                    db.session.add(agendamento_relatorio)
                    print(
                        f"  ✅ Agendamento de relatórios criado para {operadora.nome}")
                    agendamentos_criados += 1
                else:
                    print(
                        f"  ⚠️  Agendamento de relatórios já existe para {operadora.nome}")

            # Commit das mudanças
            db.session.commit()

            print(f"\n🎉 Agendamentos criados com sucesso!")
            print(f"📊 Total de novos agendamentos: {agendamentos_criados}")

            # Listar todos os agendamentos por operadora
            print("\n📋 Resumo dos agendamentos por operadora:")
            for operadora in operadoras:
                agendamentos_operadora = Agendamento.query.filter_by(
                    operadora_id=operadora.id
                ).all()

                print(f"\n🏢 {operadora.nome} ({operadora.codigo}):")
                if agendamentos_operadora:
                    for agendamento in agendamentos_operadora:
                        status = "✅ Ativo" if agendamento.status_ativo else "❌ Inativo"
                        print(f"  • {agendamento.nome_agendamento} - {status}")
                        print(f"    Cron: {agendamento.cron_expressao}")
                else:
                    print("  • Nenhum agendamento específico")

            # Agendamentos gerais
            agendamentos_gerais = Agendamento.query.filter_by(
                operadora_id=None).all()
            print(f"\n🌐 Agendamentos Gerais do Sistema:")
            for agendamento in agendamentos_gerais:
                status = "✅ Ativo" if agendamento.status_ativo else "❌ Inativo"
                print(f"  • {agendamento.nome_agendamento} - {status}")
                print(f"    Cron: {agendamento.cron_expressao}")

            return True

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao criar agendamentos por operadora: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    print("🚀 Script de Criação de Agendamentos por Operadora")
    print("=" * 60)

    sucesso = criar_agendamentos_por_operadora()

    if sucesso:
        print("\n✅ Script executado com sucesso!")
        print("\n📝 Funcionalidades implementadas:")
        print("✅ Agendamentos por operadora específica")
        print("✅ Downloads automáticos por operadora")
        print("✅ Relatórios específicos por operadora")
        print("✅ Filtros por operadora na interface")
        print("✅ Parâmetros específicos por operadora")
        print("\n🎯 Próximos passos:")
        print("1. Acesse o sistema em http://localhost:5050")
        print("2. Vá para o menu 'Agendamentos'")
        print("3. Use os filtros para ver agendamentos por operadora")
        print("4. Crie novos agendamentos específicos conforme necessário")
    else:
        print("\n❌ Script falhou!")
        sys.exit(1)
