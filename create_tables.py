
#!/usr/bin/env python3
"""
Script para criar todas as tabelas do banco de dados
"""

import os
import sys

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apps import create_app, db
from apps.models import Operadora, Usuario
from apps.config import config_dict

def create_tables():
    """Cria todas as tabelas do banco de dados"""
    
    # Cria a aplicação Flask
    app_config = os.environ.get('FLASK_ENV', 'Debug')
    app = create_app(config_dict[app_config])
    
    with app.app_context():
        try:
            # Remove todas as tabelas existentes (cuidado!)
            print("Removendo tabelas existentes...")
            db.drop_all()
            
            # Cria todas as tabelas
            print("Criando novas tabelas...")
            db.create_all()
            
            # Verifica se as tabelas foram criadas
            inspector = db.inspect(db.engine)
            tabelas = inspector.get_table_names()
            
            print(f"Tabelas criadas: {tabelas}")
            
            # Cria dados iniciais para teste
            criar_dados_iniciais()
            
            print("✅ Banco de dados criado com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro ao criar banco de dados: {str(e)}")
            return False
    
    return True

def criar_dados_iniciais():
    """Cria dados iniciais para teste"""
    
    # Verifica se já existem operadoras
    if Operadora.query.count() > 0:
        print("Dados já existem, pulando criação...")
        return
    
    # Operadoras de exemplo
    operadoras_exemplo = [
        {
            'nome': 'Embratel',
            'codigo': 'EMB',
            'possui_rpa': True,
            'status_ativo': True,
            'url_portal': 'https://portal.embratel.com.br',
            'classe_rpa': 'EmbratelRPA',
            'instrucoes_acesso': 'Portal da Embratel para download de faturas'
        },
        {
            'nome': 'Vivo',
            'codigo': 'VIV',
            'possui_rpa': True,
            'status_ativo': True,
            'url_portal': 'https://meuvivo.vivo.com.br',
            'classe_rpa': 'VivoRPA',
            'instrucoes_acesso': 'Portal Meu Vivo para empresas'
        },
        {
            'nome': 'Oi',
            'codigo': 'OI',
            'possui_rpa': False,
            'status_ativo': True,
            'url_portal': 'https://www.oi.com.br',
            'instrucoes_acesso': 'Upload manual de faturas da Oi'
        },
        {
            'nome': 'TIM',
            'codigo': 'TIM',
            'possui_rpa': False,
            'status_ativo': True,
            'url_portal': 'https://www.tim.com.br',
            'instrucoes_acesso': 'Upload manual de faturas da TIM'
        },
        {
            'nome': 'Claro',
            'codigo': 'CLA',
            'possui_rpa': True,
            'status_ativo': True,
            'url_portal': 'https://www.claro.com.br',
            'classe_rpa': 'ClaroRPA',
            'instrucoes_acesso': 'Portal empresarial Claro'
        }
    ]
    
    try:
        for dados in operadoras_exemplo:
            operadora = Operadora(**dados)
            db.session.add(operadora)
        
        db.session.commit()
        print(f"✅ Criadas {len(operadoras_exemplo)} operadoras de exemplo")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao criar dados iniciais: {str(e)}")

if __name__ == '__main__':
    print("🚀 Iniciando criação do banco de dados...")
    create_tables()
