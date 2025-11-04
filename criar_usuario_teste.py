#!/usr/bin/env python3
"""
Script para criar um usuário de teste no sistema
"""

from apps.models import Usuario, PerfilUsuario
from apps.authentication.models import Users
from apps.authentication.util import hash_pass
from apps.config import config_dict
from apps import create_app, db
import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath('.'))

# Selecionar configuração
app_config = config_dict.get(
    os.getenv('FLASK_ENV', 'Debug').capitalize(), config_dict['Debug'])


def criar_usuario_teste():
    """Cria um usuário de teste no sistema"""

    app = create_app(app_config)

    with app.app_context():
        try:
            # Verificar se já existe usuário de teste
            usuario_existente = Usuario.query.filter_by(
                email='admin@teste.com').first()
            if usuario_existente:
                print(
                    f"✅ Usuário de teste já existe: {usuario_existente.email}")
                return usuario_existente

            # Criar usuário no modelo Usuario
            usuario = Usuario(
                nome_completo="Administrador Teste",
                email="admin@teste.com",
                telefone="(11) 99999-9999",
                perfil_usuario=PerfilUsuario.ADMINISTRADOR.value,
                status_ativo=True
            )

            db.session.add(usuario)
            db.session.commit()

            print(f"✅ Usuário criado: {usuario.id}")

            # Criar usuário no modelo Users (autenticação)
            auth_user = Users(
                username="admin",
                email="admin@teste.com",
                password="admin123"  # O modelo já faz o hash automaticamente
            )

            db.session.add(auth_user)
            db.session.commit()

            print(f"✅ Usuário de autenticação criado: {auth_user.id}")

            print("\n📋 Credenciais de Teste:")
            print("Username: admin")
            print("Email: admin@teste.com")
            print("Senha: admin123")

            return usuario

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao criar usuário: {e}")
            import traceback
            traceback.print_exc()
            return None


if __name__ == "__main__":
    print("👤 Criando Usuário de Teste")
    print("=" * 50)

    usuario = criar_usuario_teste()

    if usuario:
        print("\n🎉 Usuário de teste criado com sucesso!")
    else:
        print("\n💥 Falha ao criar usuário de teste.")
