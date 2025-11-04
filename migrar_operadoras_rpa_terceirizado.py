#!/usr/bin/env python3
"""
Script para migrar banco de dados - Adicionar campos RPA terceirizado
"""

import logging
from apps import create_app, db
from sqlalchemy import text
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrar_operadoras_rpa():
    """Adiciona campos para RPA terceirizado na tabela operadoras"""

    try:
        # Verificar se as colunas já existem
        result = db.session.execute(text("PRAGMA table_info(operadoras)"))
        colunas_existentes = [row[1] for row in result.fetchall()]

        logger.info(f"Colunas existentes: {colunas_existentes}")

        # Lista de colunas a serem adicionadas
        novas_colunas = [
            ("url_endpoint_rpa", "VARCHAR(500)"),
            ("rpa_auth_token", "VARCHAR(500)"),
            ("rpa_terceirizado", "BOOLEAN DEFAULT 0 NOT NULL")
        ]

        # Adicionar colunas que não existem
        for nome_coluna, tipo_coluna in novas_colunas:
            if nome_coluna not in colunas_existentes:
                sql = f"ALTER TABLE operadoras ADD COLUMN {nome_coluna} {tipo_coluna}"
                logger.info(f"Executando: {sql}")
                db.session.execute(text(sql))
                logger.info(f"✅ Coluna {nome_coluna} adicionada com sucesso")
            else:
                logger.info(f"⏭️  Coluna {nome_coluna} já existe, pulando...")

        # Commit das alterações
        db.session.commit()
        logger.info("✅ Migração concluída com sucesso!")

        # Mostrar estrutura atualizada
        result = db.session.execute(text("PRAGMA table_info(operadoras)"))
        print("\n📋 Estrutura atual da tabela operadoras:")
        for row in result.fetchall():
            print(f"  - {row[1]} ({row[2]})")

    except Exception as e:
        logger.error(f"❌ Erro na migração: {str(e)}")
        db.session.rollback()
        raise


def criar_operadora_exemplo():
    """Cria uma operadora de exemplo com RPA terceirizado"""
    try:
        from apps.models import Operadora

        # Verificar se já existe
        operadora = Operadora.query.filter_by(codigo='EMB_TERC').first()
        if operadora:
            logger.info("⏭️  Operadora exemplo já existe")
            return

        # Criar nova operadora com RPA terceirizado
        operadora = Operadora(
            nome="Embratel Terceirizado",
            codigo="EMB_TERC",
            possui_rpa=True,
            status_ativo=True,
            url_portal="https://portal.embratel.com.br",
            classe_rpa="EmbratelRPA",
            rpa_terceirizado=True,
            url_endpoint_rpa="https://rpa-terceirizado.com/api/v1/executar-download",
            rpa_auth_token="Bearer exemplo-token-123"
        )

        db.session.add(operadora)
        db.session.commit()

        logger.info("✅ Operadora exemplo criada com sucesso!")
        logger.info(f"   ID: {operadora.id}")
        logger.info(f"   Nome: {operadora.nome}")
        logger.info(f"   RPA Terceirizado: {operadora.rpa_terceirizado}")
        logger.info(f"   Endpoint RPA: {operadora.url_endpoint_rpa}")

    except Exception as e:
        logger.error(f"❌ Erro ao criar operadora exemplo: {str(e)}")
        db.session.rollback()
        raise


if __name__ == "__main__":
    print("🚀 Iniciando migração do banco de dados...")

    app = create_app()

    with app.app_context():
        # 1. Migrar estrutura da tabela
        migrar_operadoras_rpa()

        # 2. Criar operadora exemplo
        criar_operadora_exemplo()

        print("\n✅ Migração concluída com sucesso!")
        print("\n📝 Próximos passos:")
        print("1. Configure os endpoints RPA nas operadoras existentes")
        print("2. Teste a integração com RPAs terceirizados")
        print("3. Valide os formulários de cadastro de operadoras")
