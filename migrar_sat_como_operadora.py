#!/usr/bin/env python3
"""
Script para migrar SAT como operadora universal
"""

import logging
from apps.models import Operadora, Cliente
from apps import create_app, db
from sqlalchemy import text
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def criar_operadora_sat():
    """Cria operadora SAT universal se não existir"""

    try:
        # Verificar se SAT já existe
        sat_operadora = Operadora.query.filter_by(codigo='SAT').first()
        if sat_operadora:
            logger.info("⏭️  Operadora SAT já existe")
            return sat_operadora

        # Criar operadora SAT universal
        sat_operadora = Operadora(
            nome="SAT - Sistema BEG",
            codigo="SAT",
            possui_rpa=True,
            status_ativo=True,
            url_portal="https://sat.begtelecomunicacoes.com.br",
            instrucoes_acesso="Sistema SAT universal para upload de faturas - RPA TERCEIRIZADO",
            classe_rpa="SatRPA",
            configuracao_rpa={
                "classe_rpa": "SatRPA",
                "timeout_padrao": 180,
                "tentativas_maximas": 3,
                "parametros_especiais": {
                    "tipo_upload": "universal",
                    "formato_arquivo": "pdf",
                    "validacao_dados": True,
                    "terceirizado": True
                }
            },
            # SAT configurado como RPA TERCEIRIZADO
            rpa_terceirizado=True,  # SAT é RPA externo/terceirizado
            # SAT usa endpoint unificado
            url_endpoint_rpa="https://sat-terceirizado.begtelecomunicacoes.com.br/api/v1/upload-fatura",
            rpa_auth_token="Bearer sat_token_terceirizado_aqui"
        )

        db.session.add(sat_operadora)
        db.session.commit()

        logger.info("✅ Operadora SAT criada com sucesso!")
        logger.info(f"   ID: {sat_operadora.id}")
        logger.info(f"   Nome: {sat_operadora.nome}")
        logger.info(f"   Código: {sat_operadora.codigo}")

        return sat_operadora

    except Exception as e:
        logger.error(f"❌ Erro ao criar operadora SAT: {str(e)}")
        db.session.rollback()
        raise


def migrar_relacionamento_cliente_sat():
    """Migra relacionamento de clientes para incluir SAT"""

    try:
        # Primeiro, precisamos alterar a estrutura para suportar múltiplas operadoras
        logger.info(
            "🔄 Verificando estrutura de relacionamento cliente-operadora...")

        # Por enquanto, vamos criar um campo para rastrear vinculação SAT
        # Verificar se a coluna já existe
        result = db.session.execute(text("PRAGMA table_info(clientes)"))
        colunas_existentes = [row[1] for row in result.fetchall()]

        if 'vinculado_sat' not in colunas_existentes:
            sql = "ALTER TABLE clientes ADD COLUMN vinculado_sat BOOLEAN DEFAULT 1 NOT NULL"
            logger.info(f"Executando: {sql}")
            db.session.execute(text(sql))
            db.session.commit()
            logger.info("✅ Coluna vinculado_sat adicionada")

        # Atualizar todos os clientes para estar vinculados ao SAT
        clientes = Cliente.query.all()
        logger.info(f"📊 Processando {len(clientes)} clientes...")

        for cliente in clientes:
            # Todos os clientes devem ter vinculação com SAT
            sql = "UPDATE clientes SET vinculado_sat = 1 WHERE id = :cliente_id"
            db.session.execute(text(sql), {"cliente_id": str(cliente.id)})

        db.session.commit()
        logger.info("✅ Todos os clientes vinculados ao SAT")

    except Exception as e:
        logger.error(f"❌ Erro ao migrar relacionamento: {str(e)}")
        db.session.rollback()
        raise


def validar_dados_sat_clientes():
    """Valida se todos os clientes têm dados SAT necessários"""

    try:
        clientes_sem_dados_sat = []
        clientes = Cliente.query.all()

        for cliente in clientes:
            problemas = []

            if not cliente.nome_sat:
                problemas.append("nome_sat vazio")

            if not cliente.dados_sat:
                problemas.append("dados_sat vazio")

            if problemas:
                clientes_sem_dados_sat.append({
                    'id': str(cliente.id),
                    'razao_social': cliente.razao_social,
                    'problemas': problemas
                })

        if clientes_sem_dados_sat:
            logger.warning(
                f"⚠️  {len(clientes_sem_dados_sat)} clientes com dados SAT incompletos:")
            # Mostra só os primeiros 5
            for cliente in clientes_sem_dados_sat[:5]:
                logger.warning(
                    f"   - {cliente['razao_social']}: {', '.join(cliente['problemas'])}")

            if len(clientes_sem_dados_sat) > 5:
                logger.warning(
                    f"   ... e mais {len(clientes_sem_dados_sat) - 5} clientes")
        else:
            logger.info("✅ Todos os clientes têm dados SAT completos")

        return clientes_sem_dados_sat

    except Exception as e:
        logger.error(f"❌ Erro ao validar dados SAT: {str(e)}")
        raise


def atualizar_concentrador_rpa():
    """Atualiza lógica do concentrador para SAT como operadora"""

    logger.info("📝 Instruções para atualizar ConcentradorRPA:")
    logger.info("1. SAT está registrado como RPA código 'SAT'")
    logger.info("2. Todos os uploads SAT são direcionados para SatRPA")
    logger.info("3. Clientes agora têm vinculação formal com SAT")
    logger.info("4. Dados SAT específicos mantidos no cliente")


def criar_processo_exemplo_sat():
    """Cria um exemplo de processo que usa SAT"""

    try:
        # Buscar operadora SAT
        sat_operadora = Operadora.query.filter_by(codigo='SAT').first()
        if not sat_operadora:
            logger.warning("⚠️  Operadora SAT não encontrada")
            return

        # Buscar um cliente exemplo
        cliente_exemplo = Cliente.query.first()
        if not cliente_exemplo:
            logger.warning("⚠️  Nenhum cliente encontrado")
            return

        logger.info("✅ Estrutura pronta para processos SAT:")
        logger.info(
            f"   - Operadora SAT: {sat_operadora.nome} (ID: {sat_operadora.id})")
        logger.info(f"   - Cliente exemplo: {cliente_exemplo.razao_social}")
        logger.info(f"   - RPA SAT: {sat_operadora.classe_rpa}")
        logger.info(
            f"   - Dados SAT cliente: {cliente_exemplo.dados_sat[:50] if cliente_exemplo.dados_sat else 'Não definido'}")

    except Exception as e:
        logger.error(f"❌ Erro ao criar exemplo: {str(e)}")


if __name__ == "__main__":
    print("🚀 Iniciando migração SAT como operadora...")

    app = create_app()

    with app.app_context():
        # 1. Criar operadora SAT
        sat_operadora = criar_operadora_sat()

        # 2. Migrar relacionamento cliente-SAT
        migrar_relacionamento_cliente_sat()

        # 3. Validar dados SAT dos clientes
        clientes_problemas = validar_dados_sat_clientes()

        # 4. Atualizar concentrador RPA
        atualizar_concentrador_rpa()

        # 5. Criar exemplo
        criar_processo_exemplo_sat()

        print("\n✅ Migração SAT concluída com sucesso!")

        print("\n📋 Resumo da implementação:")
        print("✅ SAT criado como operadora universal")
        print("✅ Todos os clientes vinculados ao SAT")
        print("✅ Dados SAT validados nos clientes")
        print("✅ ConcentradorRPA já suporta SAT")

        if clientes_problemas:
            print(
                f"\n⚠️  ATENÇÃO: {len(clientes_problemas)} clientes precisam de dados SAT completos")

        print("\n📝 Próximos passos:")
        print("1. Completar dados SAT nos clientes que precisarem")
        print("2. Testar fluxo de upload SAT")
        print("3. Validar relacionamento múltiplas operadoras")
        print("4. Implementar tabela de relacionamento N:N se necessário")
