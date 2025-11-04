#!/usr/bin/env python3
"""
Script para migrar a tabela de agendamentos e adicionar a coluna de operadora
"""

from sqlalchemy import text
from apps.models import Agendamento, Operadora
from apps import create_app, db
import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def migrar_agendamentos_operadora():
    """Migra a tabela de agendamentos para incluir a coluna de operadora"""

    app = create_app()

    with app.app_context():
        try:
            print("🔄 Migrando tabela de agendamentos...")

            # Verificar se a coluna operadora_id já existe
            inspector = db.inspect(db.engine)
            colunas = [col['name']
                       for col in inspector.get_columns('agendamentos')]

            if 'operadora_id' in colunas:
                print("✅ Coluna operadora_id já existe na tabela agendamentos")
                return True

            # Adicionar a coluna operadora_id
            print("➕ Adicionando coluna operadora_id...")
            db.session.execute(text("""
                ALTER TABLE agendamentos
                ADD COLUMN operadora_id CHAR(36) REFERENCES operadoras(id) ON DELETE CASCADE
            """))

            # Criar índice na coluna operadora_id
            print("📊 Criando índice na coluna operadora_id...")
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_agendamentos_operadora_id
                ON agendamentos(operadora_id)
            """))

            db.session.commit()
            print("✅ Migração concluída com sucesso!")

            # Verificar agendamentos existentes
            agendamentos_existentes = Agendamento.query.count()
            print(
                f"📋 Total de agendamentos no sistema: {agendamentos_existentes}")

            if agendamentos_existentes > 0:
                print("\n📝 Agendamentos existentes:")
                agendamentos = Agendamento.query.all()
                for i, agendamento in enumerate(agendamentos, 1):
                    operadora_info = f" - Operadora: {agendamento.operadora.nome}" if agendamento.operadora else " - Operadora: Geral"
                    print(
                        f"  {i}. {agendamento.nome_agendamento}{operadora_info}")
                    print(f"     Tipo: {agendamento.tipo_agendamento}")
                    print(f"     Cron: {agendamento.cron_expressao}")
                    print()

            return True

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro na migração: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    print("🚀 Script de Migração - Agendamentos por Operadora")
    print("=" * 60)

    sucesso = migrar_agendamentos_operadora()

    if sucesso:
        print("\n✅ Migração executada com sucesso!")
        print("\n📝 Próximos passos:")
        print("1. Acesse o sistema em http://localhost:5050")
        print("2. Vá para o menu 'Agendamentos'")
        print("3. Crie novos agendamentos específicos por operadora")
        print("4. Edite agendamentos existentes para associar a operadoras")
    else:
        print("\n❌ Migração falhou!")
        sys.exit(1)
