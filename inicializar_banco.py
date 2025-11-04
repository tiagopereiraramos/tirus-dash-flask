#!/usr/bin/env python3
"""
Script simples para inicializar o banco de dados
"""

from apps.models.operadora import Operadora
from apps.models.usuario import Usuario
from apps import create_app, db
import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath('.'))


def inicializar_banco():
    """Inicializa o banco de dados com as tabelas necessárias"""
    print("🚀 Inicializando banco de dados...")

    app = create_app()

    with app.app_context():
        try:
            # Criar todas as tabelas
            print("📋 Criando tabelas...")
            db.create_all()

            # Verificar se as tabelas foram criadas
            inspector = db.inspect(db.engine)
            tabelas = inspector.get_table_names()
            print(f"✅ Tabelas criadas: {tabelas}")

            # Verificar estrutura da tabela usuarios
            if 'usuarios' in tabelas:
                result = db.session.execute("PRAGMA table_info(usuarios);")
                colunas = [row[1] for row in result.fetchall()]
                print(f"📋 Colunas da tabela usuarios: {colunas}")

                # Verificar se as colunas de autenticação existem
                colunas_necessarias = ['username', 'password_hash']
                for coluna in colunas_necessarias:
                    if coluna not in colunas:
                        print(f"➕ Adicionando coluna {coluna}...")
                        db.session.execute(
                            f"ALTER TABLE usuarios ADD COLUMN {coluna} VARCHAR(255);")

                # Criar índice único para username
                try:
                    db.session.execute(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ix_usuarios_username ON usuarios (username);")
                    print("✅ Índice único para username criado")
                except Exception as e:
                    print(f"⚠️  Índice já existe: {e}")

                db.session.commit()
                print("✅ Banco de dados inicializado com sucesso!")
                return True
            else:
                print("❌ Tabela usuarios não foi criada!")
                return False

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao inicializar banco: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    sucesso = inicializar_banco()
    if sucesso:
        print("\n🎉 Banco de dados inicializado com sucesso!")
    else:
        print("\n💥 Falha na inicialização do banco!")
