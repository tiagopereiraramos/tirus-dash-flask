#!/usr/bin/env python3
"""
Script para atualizar o status dos processos que têm dados completos
(URL, data de vencimento e valor) mas ainda estão em AGUARDANDO_DOWNLOAD
"""

from sqlalchemy import text
from apps.models import Processo
from apps import create_app, db
from apps.config import config_dict
import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath('.'))

# Selecionar configuração igual ao run.py
app_config = config_dict.get(
    os.getenv('FLASK_ENV', 'Debug').capitalize(), config_dict['Debug'])


def atualizar_status_processos_completos():
    """Atualiza processos que têm dados completos para AGUARDANDO_APROVACAO"""

    app = create_app(app_config)

    with app.app_context():
        print("Iniciando atualização de processos com dados completos...")

        try:
            # Buscar processos que têm dados completos mas estão em AGUARDANDO_DOWNLOAD
            processos_para_atualizar = db.session.execute(
                text("""
                    SELECT id, cliente_id, mes_ano, url_fatura, data_vencimento, valor_fatura, status_processo
                    FROM processos
                    WHERE status_processo = 'AGUARDANDO_DOWNLOAD'
                    AND url_fatura IS NOT NULL
                    AND url_fatura != ''
                    AND data_vencimento IS NOT NULL
                    AND valor_fatura IS NOT NULL
                    AND valor_fatura > 0
                """)
            ).fetchall()

            print(
                f"Encontrados {len(processos_para_atualizar)} processos com dados completos")

            if processos_para_atualizar:
                # Atualizar status para AGUARDANDO_APROVACAO
                result = db.session.execute(
                    text("""
                        UPDATE processos
                        SET status_processo = 'AGUARDANDO_APROVACAO'
                        WHERE status_processo = 'AGUARDANDO_DOWNLOAD'
                        AND url_fatura IS NOT NULL
                        AND url_fatura != ''
                        AND data_vencimento IS NOT NULL
                        AND valor_fatura IS NOT NULL
                        AND valor_fatura > 0
                    """)
                )

                db.session.commit()
                print(
                    f"✅ Atualizados {result.rowcount} processos para AGUARDANDO_APROVACAO")

                # Mostrar detalhes dos processos atualizados
                print("\nDetalhes dos processos atualizados:")
                for processo in processos_para_atualizar:
                    print(f"  - ID: {processo.id}")
                    print(f"    Cliente ID: {processo.cliente_id}")
                    print(f"    Mês/Ano: {processo.mes_ano}")
                    print(f"    URL: {processo.url_fatura}")
                    print(f"    Vencimento: {processo.data_vencimento}")
                    print(f"    Valor: R$ {processo.valor_fatura}")
                    print()
            else:
                print("ℹ️  Nenhum processo encontrado para atualização")

            # Mostrar estatísticas finais
            print("\nEstatísticas finais:")
            for status in ['AGUARDANDO_DOWNLOAD', 'AGUARDANDO_APROVACAO', 'AGUARDANDO_ENVIO_SAT', 'UPLOAD_REALIZADO']:
                count = db.session.execute(
                    text(
                        "SELECT COUNT(*) FROM processos WHERE status_processo = :status"),
                    {'status': status}
                ).scalar()
                print(f"  {status}: {count} processos")

            # Mostrar processos que ainda precisam de atenção
            processos_incompletos = db.session.execute(
                text("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN url_fatura IS NULL OR url_fatura = '' THEN 1 ELSE 0 END) as sem_url,
                           SUM(CASE WHEN data_vencimento IS NULL THEN 1 ELSE 0 END) as sem_vencimento,
                           SUM(CASE WHEN valor_fatura IS NULL OR valor_fatura = 0 THEN 1 ELSE 0 END) as sem_valor
                    FROM processos
                    WHERE status_processo = 'AGUARDANDO_DOWNLOAD'
                """)
            ).fetchone()

            if processos_incompletos.total > 0:
                print(f"\nProcessos em AGUARDANDO_DOWNLOAD que ainda precisam de dados:")
                print(f"  Total: {processos_incompletos.total}")
                print(f"  Sem URL: {processos_incompletos.sem_url}")
                print(
                    f"  Sem data de vencimento: {processos_incompletos.sem_vencimento}")
                print(f"  Sem valor: {processos_incompletos.sem_valor}")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao atualizar status: {e}")
            raise


if __name__ == "__main__":
    atualizar_status_processos_completos()
