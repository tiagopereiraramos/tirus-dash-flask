#!/usr/bin/env python3
"""
Script para migrar o banco de dados, adicionando colunas de autenticação à tabela usuarios
"""

from apps.config import config_dict
from apps import create_app, db
import os
import sys
from sqlalchemy import text

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath('.'))

# Selecionar configuração
app_config = config_dict.get(
    os.getenv('FLASK_ENV', 'Debug').capitalize(), config_dict['Debug'])


def migrar_banco_usuarios():
    """Migra o banco de dados para adicionar colunas de autenticação"""

    app = create_app()

    with app.app_context():
        try:
            print("🔄 Migrando banco de dados para nova estrutura de usuários...")

            # Verificar se as colunas já existem
            result = db.session.execute(text("""
                PRAGMA table_info(usuarios);
            """))
            colunas_existentes = [row[1] for row in result.fetchall()]

            print(
                f"📋 Colunas existentes na tabela usuarios: {colunas_existentes}")

            # Adicionar coluna username se não existir
            if 'username' not in colunas_existentes:
                print("➕ Adicionando coluna 'username'...")
                db.session.execute(text("""
                    ALTER TABLE usuarios ADD COLUMN username VARCHAR(64);
                """))
                print("✅ Coluna 'username' adicionada")
            else:
                print("✅ Coluna 'username' já existe")

            # Adicionar coluna password_hash se não existir
            if 'password_hash' not in colunas_existentes:
                print("➕ Adicionando coluna 'password_hash'...")
                db.session.execute(text("""
                    ALTER TABLE usuarios ADD COLUMN password_hash VARCHAR(255);
                """))
                print("✅ Coluna 'password_hash' adicionada")
            else:
                print("✅ Coluna 'password_hash' já existe")

            # Criar índices únicos se não existirem
            try:
                print("🔗 Criando índice único para username...")
                db.session.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS ix_usuarios_username ON usuarios (username);
                """))
                print("✅ Índice único para username criado")
            except Exception as e:
                print(f"⚠️  Índice para username já existe ou erro: {e}")

            db.session.commit()
            print("✅ Migração do banco concluída com sucesso!")

            # Verificar estrutura final
            result = db.session.execute(text("""
                PRAGMA table_info(usuarios);
            """))
            colunas_finais = [row[1] for row in result.fetchall()]
            print(f"📋 Estrutura final da tabela usuarios: {colunas_finais}")

            return True

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro na migração do banco: {e}")
            import traceback
            traceback.print_exc()
            return False


def verificar_estrutura():
    """Verifica se a estrutura está correta"""

    app = create_app()

    with app.app_context():
        try:
            print("\n🔍 Verificando estrutura do banco...")

            # Verificar colunas da tabela usuarios
            result = db.session.execute(text("""
                PRAGMA table_info(usuarios);
            """))
            colunas = [row[1] for row in result.fetchall()]

            print(f"📋 Colunas da tabela usuarios: {colunas}")

            # Verificar se as colunas necessárias existem
            colunas_necessarias = ['username', 'password_hash']
            colunas_faltando = [
                col for col in colunas_necessarias if col not in colunas]

            if colunas_faltando:
                print(f"❌ Colunas faltando: {colunas_faltando}")
                return False
            else:
                print("✅ Todas as colunas necessárias existem!")
                return True

        except Exception as e:
            print(f"❌ Erro ao verificar estrutura: {e}")
            return False


if __name__ == "__main__":
    print("🗄️  Migração do Banco de Dados - Usuários")
    print("=" * 50)

    # Migrar banco
    sucesso = migrar_banco_usuarios()

    if sucesso:
        # Verificar estrutura
        estrutura_ok = verificar_estrutura()

        if estrutura_ok:
            print("\n🎉 Migração do banco concluída com sucesso!")
            print("📋 Agora você pode migrar os usuários.")
        else:
            print("\n💥 Estrutura do banco incorreta!")
    else:
        print("\n💥 Falha na migração do banco!")
