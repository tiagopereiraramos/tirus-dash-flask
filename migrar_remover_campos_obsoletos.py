#!/usr/bin/env python3
"""
Script para remover campos obsoletos do modelo Operadora
- url_endpoint_sat (VARCHAR(500)) - SAT agora é operadora comum
- classe_rpa (VARCHAR(100)) - Não mais usado com RPAs terceirizados
"""

import logging
from apps import create_app, db
from sqlalchemy import text
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def remover_campos_obsoletos():
    """Remove campos obsoletos da tabela operadoras"""

    try:
        # Verificar se as colunas existem antes de tentar remover
        result = db.session.execute(text("PRAGMA table_info(operadoras)"))
        colunas_existentes = [row[1] for row in result.fetchall()]

        logger.info(f"Colunas existentes: {colunas_existentes}")

        # Lista de colunas a serem removidas
        colunas_remover = ["url_endpoint_sat", "classe_rpa"]

        # Verificar quais colunas existem e precisam ser removidas
        colunas_para_remover = [
            col for col in colunas_remover if col in colunas_existentes]

        if not colunas_para_remover:
            logger.info("✅ Nenhuma coluna obsoleta encontrada para remover")
            return

        logger.info(f"🔧 Colunas a serem removidas: {colunas_para_remover}")

        # SQLite não suporta DROP COLUMN diretamente
        # Precisamos criar uma nova tabela sem as colunas e migrar os dados

        # 1. Backup da tabela atual
        logger.info("📋 Criando backup da tabela operadoras...")
        db.session.execute(text("""
            CREATE TABLE operadoras_backup AS
            SELECT * FROM operadoras
        """))

        # 2. Criar nova tabela sem as colunas obsoletas
        logger.info("🏗️ Criando nova estrutura da tabela operadoras...")
        db.session.execute(text("""
            CREATE TABLE operadoras_new (
                nome VARCHAR(100) NOT NULL UNIQUE,
                codigo VARCHAR(20) NOT NULL UNIQUE,
                possui_rpa BOOLEAN NOT NULL DEFAULT 0,
                status_ativo BOOLEAN NOT NULL DEFAULT 1,
                url_portal VARCHAR(500),
                instrucoes_acesso TEXT,
                configuracao_rpa JSON,
                id CHAR(36) NOT NULL,
                data_criacao DATETIME,
                data_atualizacao DATETIME,
                url_endpoint_rpa VARCHAR(500),
                rpa_auth_token VARCHAR(500),
                rpa_terceirizado BOOLEAN NOT NULL DEFAULT 0,
                PRIMARY KEY (id)
            )
        """))

        # 3. Migrar dados (excluindo as colunas removidas)
        logger.info("📦 Migrando dados para nova estrutura...")
        db.session.execute(text("""
            INSERT INTO operadoras_new (
                nome, codigo, possui_rpa, status_ativo, url_portal,
                instrucoes_acesso, configuracao_rpa, id, data_criacao,
                data_atualizacao, url_endpoint_rpa, rpa_auth_token, rpa_terceirizado
            )
            SELECT
                nome, codigo, possui_rpa, status_ativo, url_portal,
                instrucoes_acesso, configuracao_rpa, id, data_criacao,
                data_atualizacao, url_endpoint_rpa, rpa_auth_token, rpa_terceirizado
            FROM operadoras
        """))

        # 4. Remover tabela antiga e renomear nova
        logger.info("🔄 Substituindo tabela antiga...")
        db.session.execute(text("DROP TABLE operadoras"))
        db.session.execute(
            text("ALTER TABLE operadoras_new RENAME TO operadoras"))

        # 5. Recriar índices
        logger.info("📊 Recriando índices...")
        db.session.execute(
            text("CREATE UNIQUE INDEX idx_operadoras_nome ON operadoras(nome)"))
        db.session.execute(
            text("CREATE UNIQUE INDEX idx_operadoras_codigo ON operadoras(codigo)"))
        db.session.execute(
            text("CREATE INDEX idx_operadoras_status_ativo ON operadoras(status_ativo)"))

        # Commit das alterações
        db.session.commit()
        logger.info("✅ Migração concluída com sucesso!")

        # Mostrar estrutura atualizada
        result = db.session.execute(text("PRAGMA table_info(operadoras)"))
        print("\n📋 Estrutura atual da tabela operadoras:")
        for row in result.fetchall():
            print(f"  - {row[1]} ({row[2]})")

        logger.info("\n🎯 Campos removidos com sucesso:")
        for campo in colunas_para_remover:
            logger.info(f"  ❌ {campo}")

        logger.info("\n📈 Benefícios da remoção:")
        logger.info(
            "  ✅ url_endpoint_sat: SAT agora é operadora comum com url_endpoint_rpa")
        logger.info(
            "  ✅ classe_rpa: RPAs terceirizados não usam classe Python local")

    except Exception as e:
        logger.error(f"❌ Erro na migração: {str(e)}")
        db.session.rollback()

        # Tentar restaurar backup se algo deu errado
        try:
            logger.info("🔄 Tentando restaurar backup...")
            db.session.execute(text("DROP TABLE IF EXISTS operadoras"))
            db.session.execute(
                text("ALTER TABLE operadoras_backup RENAME TO operadoras"))
            db.session.commit()
            logger.info("✅ Backup restaurado com sucesso")
        except Exception as restore_error:
            logger.error(f"❌ Erro ao restaurar backup: {str(restore_error)}")

        raise


def validar_remocao():
    """Valida se a remoção foi bem-sucedida"""
    try:
        result = db.session.execute(text("PRAGMA table_info(operadoras)"))
        colunas_atuais = [row[1] for row in result.fetchall()]

        campos_removidos = ["url_endpoint_sat", "classe_rpa"]
        campos_ainda_existentes = [
            campo for campo in campos_removidos if campo in colunas_atuais]

        if campos_ainda_existentes:
            logger.error(f"❌ Campos ainda existem: {campos_ainda_existentes}")
            return False

        logger.info("✅ Validação: Todos os campos obsoletos foram removidos")
        return True

    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        return False


def limpar_backup():
    """Remove a tabela de backup após confirmação"""
    try:
        db.session.execute(text("DROP TABLE IF EXISTS operadoras_backup"))
        db.session.commit()
        logger.info("🧹 Tabela de backup removida")
    except Exception as e:
        logger.error(f"⚠️ Erro ao remover backup: {str(e)}")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        logger.info("🚀 Iniciando remoção de campos obsoletos...")

        # Executar migração
        remover_campos_obsoletos()

        # Validar resultado
        if validar_remocao():
            logger.info("\n🎉 Migração concluída com sucesso!")

            # Perguntar se deve limpar backup
            resposta = input("\nDeseja remover a tabela de backup? (s/N): ")
            if resposta.lower() in ['s', 'sim', 'y', 'yes']:
                limpar_backup()
            else:
                logger.info(
                    "📦 Tabela de backup mantida como 'operadoras_backup'")
        else:
            logger.error("❌ Migração falhou na validação")
