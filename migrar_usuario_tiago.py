#!/usr/bin/env python3
"""
Script para migrar o usuário 'tiago' da estrutura antiga para a nova estrutura unificada
"""

from apps.models import Usuario, PerfilUsuario
from apps.authentication.models import Users
from apps.authentication.util import verify_pass
from apps.config import config_dict
from apps import create_app, db
import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath('.'))

# Selecionar configuração
app_config = config_dict.get(
    os.getenv('FLASK_ENV', 'Debug').capitalize(), config_dict['Debug'])


def migrar_usuario_tiago():
    """Migra o usuário 'tiago' para a nova estrutura unificada"""

    app = create_app(app_config)

    with app.app_context():
        try:
            print("🔄 Migrando usuário 'tiago' para nova estrutura...")

            # Verificar se já existe usuário 'tiago' na nova estrutura
            usuario_existente = Usuario.query.filter_by(
                username='tiago').first()
            if usuario_existente:
                print(
                    f"✅ Usuário 'tiago' já existe na nova estrutura: {usuario_existente.id}")
                return usuario_existente

            # Verificar se existe na estrutura antiga (Users)
            auth_user = Users.query.filter_by(username='tiago').first()

            if auth_user:
                print(
                    f"📋 Encontrado usuário 'tiago' na estrutura antiga: {auth_user.id}")

                # Criar usuário na nova estrutura
                usuario = Usuario(
                    nome_completo="Tiago Pereira Ramos",
                    email="tiago@begtelecomunicacoes.com.br",
                    username="tiago",
                    telefone="(11) 99999-9999",
                    perfil_usuario=PerfilUsuario.ADMINISTRADOR.value,
                    status_ativo=True
                )

                # Definir senha (assumindo que é 'tiago123' ou verificar se existe)
                senha = "tiago123"  # Você pode alterar esta senha
                usuario.set_password(senha)

                db.session.add(usuario)
                db.session.commit()

                print(f"✅ Usuário 'tiago' migrado com sucesso: {usuario.id}")
                print(f"📋 Credenciais: username=tiago, senha={senha}")

                return usuario

            else:
                print("❌ Usuário 'tiago' não encontrado na estrutura antiga")
                print("🔧 Criando novo usuário 'tiago'...")

                # Criar usuário 'tiago' do zero
                usuario = Usuario(
                    nome_completo="Tiago Pereira Ramos",
                    email="tiago@begtelecomunicacoes.com.br",
                    username="tiago",
                    telefone="(11) 99999-9999",
                    perfil_usuario=PerfilUsuario.ADMINISTRADOR.value,
                    status_ativo=True
                )

                # Definir senha
                senha = "tiago123"  # Você pode alterar esta senha
                usuario.set_password(senha)

                db.session.add(usuario)
                db.session.commit()

                print(f"✅ Usuário 'tiago' criado com sucesso: {usuario.id}")
                print(f"📋 Credenciais: username=tiago, senha={senha}")

                return usuario

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao migrar usuário 'tiago': {e}")
            import traceback
            traceback.print_exc()
            return None


def verificar_migracao():
    """Verifica se a migração foi bem-sucedida"""

    app = create_app(app_config)

    with app.app_context():
        try:
            print("\n🔍 Verificando migração...")

            # Verificar na nova estrutura
            usuario = Usuario.query.filter_by(username='tiago').first()
            if usuario:
                print(f"✅ Usuário 'tiago' encontrado na nova estrutura:")
                print(f"   ID: {usuario.id}")
                print(f"   Nome: {usuario.nome_completo}")
                print(f"   Email: {usuario.email}")
                print(f"   Username: {usuario.username}")
                print(f"   Perfil: {usuario.perfil_usuario}")
                print(
                    f"   Status: {'Ativo' if usuario.status_ativo else 'Inativo'}")

                # Testar autenticação
                if usuario.check_password("tiago123"):
                    print("✅ Senha válida!")
                else:
                    print("❌ Senha inválida!")

                return True
            else:
                print("❌ Usuário 'tiago' não encontrado na nova estrutura")
                return False

        except Exception as e:
            print(f"❌ Erro ao verificar migração: {e}")
            return False


if __name__ == "__main__":
    print("👤 Migração do Usuário 'tiago'")
    print("=" * 50)

    # Migrar usuário
    usuario = migrar_usuario_tiago()

    if usuario:
        # Verificar migração
        sucesso = verificar_migracao()

        if sucesso:
            print("\n🎉 Migração concluída com sucesso!")
            print("📋 Agora você pode fazer login com:")
            print("   Username: tiago")
            print("   Senha: tiago123")
        else:
            print("\n💥 Migração falhou na verificação!")
    else:
        print("\n💥 Falha na migração!")
