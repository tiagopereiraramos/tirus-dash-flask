#!/usr/bin/env python3
"""
Script para limpar o banco de dados mantendo apenas os usuários
"""

from apps.models import (
    Cliente, Operadora, Processo, Agendamento,
    Usuario, Execucao, Notificacao
)
from apps import create_app, db
import os
import sys
from datetime import datetime

# Adicionar o diretório do projeto ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def limpar_banco_manter_usuarios():
    """
    Limpa o banco de dados mantendo apenas os usuários
    """
    print("🧹 LIMPEZA DO BANCO DE DADOS")
    print("=" * 50)
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()

    # Criar aplicação
    app = create_app()

    with app.app_context():
        try:
            # Contar registros antes da limpeza
            print("📊 CONTAGEM ANTES DA LIMPEZA:")
            print(f"   👥 Usuários: {Usuario.query.count()}")
            print(f"   🏢 Clientes: {Cliente.query.count()}")
            print(f"   📡 Operadoras: {Operadora.query.count()}")
            print(f"   📋 Processos: {Processo.query.count()}")
            print(f"   ⏰ Agendamentos: {Agendamento.query.count()}")
            print(f"   🔄 Execuções: {Execucao.query.count()}")
            print(f"   📝 Notificações: {Notificacao.query.count()}")
            print()

            # Confirmar limpeza
            resposta = input(
                "⚠️  Tem certeza que deseja limpar o banco? (digite 'CONFIRMAR'): ").strip()

            if resposta != 'CONFIRMAR':
                print("❌ Operação cancelada pelo usuário")
                return

            print()
            print("🗑️  INICIANDO LIMPEZA...")

            # Limpar tabelas na ordem correta (respeitando foreign keys)
            print("   🗑️  Removendo Execuções...")
            Execucao.query.delete()

            print("   🗑️  Removendo Notificações...")
            Notificacao.query.delete()

            print("   🗑️  Removendo Processos...")
            Processo.query.delete()

            print("   🗑️  Removendo Agendamentos...")
            Agendamento.query.delete()

            print("   🗑️  Removendo Clientes...")
            Cliente.query.delete()

            print("   🗑️  Removendo Operadoras...")
            Operadora.query.delete()

            # Commit das alterações
            db.session.commit()

            print()
            print("✅ LIMPEZA CONCLUÍDA COM SUCESSO!")
            print()

            # Contar registros após a limpeza
            print("📊 CONTAGEM APÓS A LIMPEZA:")
            print(f"   👥 Usuários: {Usuario.query.count()}")
            print(f"   🏢 Clientes: {Cliente.query.count()}")
            print(f"   📡 Operadoras: {Operadora.query.count()}")
            print(f"   📋 Processos: {Processo.query.count()}")
            print(f"   ⏰ Agendamentos: {Agendamento.query.count()}")
            print(f"   🔄 Execuções: {Execucao.query.count()}")
            print(f"   📝 Notificações: {Notificacao.query.count()}")
            print()

            # Mostrar usuários mantidos
            usuarios = Usuario.query.all()
            print("👥 USUÁRIOS MANTIDOS:")
            for usuario in usuarios:
                print(
                    f"   • {usuario.nome_completo} ({usuario.username}) - {usuario.email}")

            print()
            print("🎉 Banco de dados limpo! Apenas os usuários foram mantidos.")
            print("💡 Agora você pode cadastrar novos dados do zero.")

        except Exception as e:
            print(f"❌ ERRO durante a limpeza: {str(e)}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    limpar_banco_manter_usuarios()
