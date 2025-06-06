
#!/usr/bin/env python3
"""
Script para atualizar os status dos processos no banco de dados
para a nova lógica simplificada
"""

import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath('.'))

from apps import create_app, db
from apps.models import Processo
from sqlalchemy import text

def update_process_status():
    """Atualiza os status dos processos para a nova lógica"""
    
    app = create_app()
    
    with app.app_context():
        print("Iniciando atualização dos status dos processos...")
        
        # Mapeamento dos status antigos para os novos
        status_mapping = {
            'DOWNLOAD_COMPLETO': 'AGUARDANDO_APROVACAO',
            'APROVADO': 'AGUARDANDO_ENVIO_SAT', 
            'ENVIADO_SAT': 'UPLOAD_REALIZADO',
            'UPLOAD_SAT_REALIZADO': 'UPLOAD_REALIZADO',
            'CONCLUIDO': 'UPLOAD_REALIZADO',
            'REJEITADO': 'AGUARDANDO_DOWNLOAD',
            'DOWNLOAD_EM_ANDAMENTO': 'AGUARDANDO_DOWNLOAD',
            'DOWNLOAD_FALHOU': 'AGUARDANDO_DOWNLOAD',
            'ENVIANDO_SAT': 'AGUARDANDO_ENVIO_SAT',
            'FALHA_ENVIO_SAT': 'AGUARDANDO_ENVIO_SAT',
            'CANCELADO': 'AGUARDANDO_DOWNLOAD'
        }
        
        try:
            # Atualizar cada status conforme o mapeamento
            for old_status, new_status in status_mapping.items():
                result = db.session.execute(
                    text("UPDATE processos SET status_processo = :new_status WHERE status_processo = :old_status"),
                    {'new_status': new_status, 'old_status': old_status}
                )
                if result.rowcount > 0:
                    print(f"Atualizados {result.rowcount} processos de '{old_status}' para '{new_status}'")
            
            # Para processos que têm url_fatura e data_vencimento mas estão em AGUARDANDO_DOWNLOAD,
            # mover para AGUARDANDO_APROVACAO
            result = db.session.execute(
                text("""
                    UPDATE processos 
                    SET status_processo = 'AGUARDANDO_APROVACAO' 
                    WHERE status_processo = 'AGUARDANDO_DOWNLOAD' 
                    AND url_fatura IS NOT NULL 
                    AND url_fatura != '' 
                    AND data_vencimento IS NOT NULL
                """)
            )
            if result.rowcount > 0:
                print(f"Movidos {result.rowcount} processos com dados completos para AGUARDANDO_APROVACAO")
            
            db.session.commit()
            print("Atualização concluída com sucesso!")
            
            # Mostrar estatísticas finais
            print("\nEstatísticas finais:")
            for status in ['AGUARDANDO_DOWNLOAD', 'AGUARDANDO_APROVACAO', 'AGUARDANDO_ENVIO_SAT', 'UPLOAD_REALIZADO']:
                count = db.session.execute(
                    text("SELECT COUNT(*) FROM processos WHERE status_processo = :status"),
                    {'status': status}
                ).scalar()
                print(f"  {status}: {count} processos")
            
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao atualizar status: {e}")
            raise

if __name__ == '__main__':
    update_process_status()
