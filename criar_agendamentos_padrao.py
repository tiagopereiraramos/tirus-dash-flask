#!/usr/bin/env python3
"""
Script para criar agendamentos padrão do sistema
"""

from apps.models import Agendamento, TipoAgendamento
from apps import create_app, db
import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def criar_agendamentos_padrao():
    """Cria agendamentos padrão do sistema"""

    app = create_app()

    with app.app_context():
        try:
            print("🔄 Criando agendamentos padrão...")

            # Verificar se já existem agendamentos
            agendamentos_existentes = Agendamento.query.count()
            if agendamentos_existentes > 0:
                print(
                    f"⚠️  Já existem {agendamentos_existentes} agendamentos no sistema.")
                resposta = input(
                    "Deseja continuar e criar os agendamentos padrão? (s/N): ")
                if resposta.lower() != 's':
                    print("❌ Operação cancelada.")
                    return False

            # 1. Agendamento para criar processos mensais
            agendamento_processos = Agendamento.criar_agendamento_processos_mensais()

            # Verificar se já existe
            existente = Agendamento.query.filter_by(
                nome_agendamento=agendamento_processos.nome_agendamento
            ).first()

            if not existente:
                db.session.add(agendamento_processos)
                print("✅ Agendamento 'Criar Processos Mensais' criado")
            else:
                print("⚠️  Agendamento 'Criar Processos Mensais' já existe")

            # 2. Agendamento para downloads automáticos
            agendamento_downloads = Agendamento.criar_agendamento_downloads()

            existente = Agendamento.query.filter_by(
                nome_agendamento=agendamento_downloads.nome_agendamento
            ).first()

            if not existente:
                db.session.add(agendamento_downloads)
                print("✅ Agendamento 'Executar Downloads Automáticos' criado")
            else:
                print("⚠️  Agendamento 'Executar Downloads Automáticos' já existe")

            # 3. Agendamento para relatórios semanais
            agendamento_relatorios = Agendamento.criar_agendamento_relatorios()

            existente = Agendamento.query.filter_by(
                nome_agendamento=agendamento_relatorios.nome_agendamento
            ).first()

            if not existente:
                db.session.add(agendamento_relatorios)
                print("✅ Agendamento 'Envio de Relatórios Semanais' criado")
            else:
                print("⚠️  Agendamento 'Envio de Relatórios Semanais' já existe")

            # 4. Agendamento para limpeza de logs (opcional)
            agendamento_limpeza = Agendamento(
                nome_agendamento="Limpeza de Logs Antigos",
                descricao="Remove logs de execução com mais de 30 dias para economizar espaço",
                cron_expressao="0 2 * * 0",  # Todo domingo às 02:00
                tipo_agendamento=TipoAgendamento.LIMPEZA_LOGS.value,
                parametros_execucao={
                    "dias_para_manter": 30,
                    "incluir_logs_erro": False
                }
            )

            existente = Agendamento.query.filter_by(
                nome_agendamento=agendamento_limpeza.nome_agendamento
            ).first()

            if not existente:
                db.session.add(agendamento_limpeza)
                print("✅ Agendamento 'Limpeza de Logs Antigos' criado")
            else:
                print("⚠️  Agendamento 'Limpeza de Logs Antigos' já existe")

            # 5. Agendamento para backup de dados (opcional)
            agendamento_backup = Agendamento(
                nome_agendamento="Backup de Dados Diário",
                descricao="Realiza backup automático dos dados do sistema",
                cron_expressao="0 1 * * *",  # Todo dia às 01:00
                tipo_agendamento=TipoAgendamento.BACKUP_DADOS.value,
                parametros_execucao={
                    "incluir_arquivos": True,
                    "comprimir_backup": True,
                    "manter_ultimos_backups": 7
                }
            )

            existente = Agendamento.query.filter_by(
                nome_agendamento=agendamento_backup.nome_agendamento
            ).first()

            if not existente:
                db.session.add(agendamento_backup)
                print("✅ Agendamento 'Backup de Dados Diário' criado")
            else:
                print("⚠️  Agendamento 'Backup de Dados Diário' já existe")

            # Commit das mudanças
            db.session.commit()

            # Listar agendamentos criados
            total_agendamentos = Agendamento.query.count()
            print(f"\n🎉 Agendamentos padrão criados com sucesso!")
            print(f"📊 Total de agendamentos no sistema: {total_agendamentos}")

            # Mostrar lista dos agendamentos
            print("\n📋 Lista de agendamentos:")
            agendamentos = Agendamento.query.all()
            for i, agendamento in enumerate(agendamentos, 1):
                status = "✅ Ativo" if agendamento.status_ativo else "❌ Inativo"
                print(f"  {i}. {agendamento.nome_agendamento} - {status}")
                print(f"     Cron: {agendamento.cron_expressao}")
                print(f"     Tipo: {agendamento.tipo_agendamento}")
                print()

            return True

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao criar agendamentos padrão: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    print("🚀 Script de Criação de Agendamentos Padrão")
    print("=" * 50)

    sucesso = criar_agendamentos_padrao()

    if sucesso:
        print("\n✅ Script executado com sucesso!")
        print("\n📝 Próximos passos:")
        print("1. Acesse o sistema em http://localhost:5050")
        print("2. Vá para o menu 'Agendamentos'")
        print("3. Verifique e ajuste os agendamentos conforme necessário")
        print("4. Implemente o executor de agendamentos (Celery/APScheduler)")
    else:
        print("\n❌ Script falhou!")
        sys.exit(1)
