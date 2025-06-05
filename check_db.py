
#!/usr/bin/env python3
"""
Script para verificar a estrutura do banco de dados
"""

import os
import sys

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apps import create_app, db
from apps.models import Operadora
from apps.config import config_dict

def check_database():
    """Verifica a estrutura e dados do banco"""
    
    app_config = os.environ.get('FLASK_ENV', 'Debug')
    app = create_app(config_dict[app_config])
    
    with app.app_context():
        try:
            # Verifica tabelas existentes
            inspector = db.inspect(db.engine)
            tabelas = inspector.get_table_names()
            
            print("📊 Tabelas no banco de dados:")
            for tabela in tabelas:
                print(f"  - {tabela}")
            
            # Verifica estrutura da tabela operadoras
            if 'operadoras' in tabelas:
                print("\n🏢 Estrutura da tabela 'operadoras':")
                colunas = inspector.get_columns('operadoras')
                for coluna in colunas:
                    print(f"  - {coluna['name']}: {coluna['type']}")
                
                # Conta registros
                total_operadoras = Operadora.query.count()
                print(f"\n📈 Total de operadoras cadastradas: {total_operadoras}")
                
                if total_operadoras > 0:
                    print("\n📋 Operadoras cadastradas:")
                    operadoras = Operadora.query.all()
                    for op in operadoras:
                        status_rpa = "✅ Com RPA" if op.possui_rpa else "📤 Upload Manual"
                        status_ativo = "🟢 Ativo" if op.status_ativo else "🔴 Inativo"
                        print(f"  - {op.codigo}: {op.nome} | {status_rpa} | {status_ativo}")
            else:
                print("❌ Tabela 'operadoras' não encontrada!")
            
        except Exception as e:
            print(f"❌ Erro ao verificar banco: {str(e)}")

if __name__ == '__main__':
    print("🔍 Verificando estrutura do banco de dados...\n")
    check_database()
