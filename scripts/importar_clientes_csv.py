"""
Script para importar clientes do CSV BGTELECOM
"""

import sys
import os
import csv
import hashlib
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from apps import create_app, db
from apps.models import Cliente, Operadora
from apps.config import config_dict


def normalizar_cnpj(cnpj: str) -> str:
    """Remove formatação do CNPJ"""
    if not cnpj:
        return ""
    return ''.join(c for c in cnpj if c.isdigit())


def normalizar_cpf(cpf: str) -> str:
    """Remove formatação do CPF"""
    if not cpf:
        return ""
    return ''.join(c for c in cpf if c.isdigit())


def limpar_texto(texto: str) -> str:
    """Remove caracteres especiais e espaços extras"""
    if not texto:
        return ""
    
    texto = texto.replace('\r', '').replace('\n', '').strip()
    
    replacements = {
        'Ã§': 'ç',
        'Ã£': 'ã',
        'Ã¡': 'á',
        'Ã©': 'é',
        'Ã­': 'í',
        'Ã³': 'ó',
        'Ãº': 'ú',
        'Ã¢': 'â',
        'Ãª': 'ê',
        'Ã´': 'ô',
        'Ã': 'Á',
        'Â': '',
        '\x81': '',
        '\x93': '',
        '\x94': ''
    }
    
    for old, new in replacements.items():
        texto = texto.replace(old, new)
    
    return texto.strip()


def importar_clientes(csv_path: str):
    """
    Importa clientes do CSV
    
    Args:
        csv_path: Caminho para o arquivo CSV
    """
    app = create_app(config_dict['Debug'])
    
    with app.app_context():
        print("=" * 80)
        print("IMPORTAÇÃO DE CLIENTES - BGTELECOM")
        print("=" * 80)
        print(f"Arquivo: {csv_path}")
        print()
        
        if not os.path.exists(csv_path):
            print(f"❌ Arquivo não encontrado: {csv_path}")
            return
        
        operadoras_cache = {}
        
        def obter_operadora(codigo: str) -> Operadora:
            """Obtém operadora do cache ou cria se não existir"""
            codigo = codigo.upper().strip()
            
            if codigo in operadoras_cache:
                return operadoras_cache[codigo]
            
            operadora = Operadora.query.filter_by(codigo=codigo).first()
            
            if not operadora:
                nome_map = {
                    'OI': 'OI S.A.',
                    'VIVO': 'Telefônica Brasil S.A.',
                    'EMBRATEL': 'Embratel',
                    'DIGITALNET': 'DigitalNet',
                    'AZUTON': 'Azuton Telecom'
                }
                
                operadora = Operadora(
                    codigo=codigo,
                    nome=nome_map.get(codigo, codigo),
                    status_ativo=True,
                    possui_rpa=True
                )
                db.session.add(operadora)
                db.session.commit()
                print(f"   ✅ Operadora '{codigo}' criada")
            
            operadoras_cache[codigo] = operadora
            return operadora
        
        total = 0
        sucesso = 0
        erros = 0
        atualizados = 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                
                for idx, row in enumerate(reader, start=2):
                    try:
                        total += 1
                        
                        hash_id = row.get('HASH', '').strip()
                        razao_social = limpar_texto(row.get('RAZÃO SOCIAL', ''))
                        nome_sat = limpar_texto(row.get('NOME SAT', ''))
                        cnpj = normalizar_cnpj(row.get('CNPJ', ''))
                        operadora_codigo = row.get('OPERADORA', '').strip().upper()
                        filtro = row.get('FILTRO', '').strip()
                        servico = limpar_texto(row.get('SERVIÇO', ''))
                        dados_sat = limpar_texto(row.get('DADOS SAT', ''))
                        unidade = limpar_texto(row.get('UNIDADE / FILTRO SAT', ''))
                        login = row.get('LOGIN ', '').strip()  # Note o espaço extra
                        senha = row.get('SENHA', '').strip()
                        cpf = normalizar_cpf(row.get('CPF', ''))
                        observacoes = limpar_texto(row.get('OBS', ''))
                        
                        if not cnpj:
                            print(f"   ⚠️  Linha {idx}: CNPJ vazio - pulando")
                            erros += 1
                            continue
                        
                        if not operadora_codigo:
                            print(f"   ⚠️  Linha {idx}: Operadora vazia - pulando")
                            erros += 1
                            continue
                        
                        operadora = obter_operadora(operadora_codigo)
                        
                        cliente_existe = Cliente.query.filter_by(cnpj=cnpj, filtro=filtro).first()
                        
                        if cliente_existe:
                            cliente_existe.razao_social = razao_social or cliente_existe.razao_social
                            cliente_existe.nome_sat = nome_sat or cliente_existe.nome_sat
                            cliente_existe.operadora_id = operadora.id
                            cliente_existe.servico = servico or cliente_existe.servico
                            cliente_existe.unidade = unidade or cliente_existe.unidade
                            cliente_existe.login_portal = login or cliente_existe.login_portal
                            cliente_existe.senha_portal = senha or cliente_existe.senha_portal
                            cliente_existe.cpf = cpf or cliente_existe.cpf
                            
                            if observacoes:
                                dados_sat_atual = cliente_existe.dados_sat or ""
                                cliente_existe.dados_sat = f"{dados_sat_atual}\nOBS: {observacoes}".strip()
                            elif dados_sat:
                                cliente_existe.dados_sat = dados_sat
                            
                            cliente_existe.status_ativo = True
                            atualizados += 1
                            
                            if total % 50 == 0:
                                print(f"   🔄 Linha {idx}: {razao_social[:40]} - ATUALIZADO")
                        else:
                            dados_sat_final = dados_sat
                            if observacoes:
                                dados_sat_final = f"{dados_sat}\nOBS: {observacoes}".strip()
                            
                            hash_unico = hashlib.md5(
                                f"{cnpj}{operadora.codigo}{servico}{filtro}{unidade}".encode()
                            ).hexdigest()[:16]
                            
                            cliente = Cliente(
                                hash_unico=hash_unico,
                                razao_social=razao_social,
                                nome_sat=nome_sat,
                                cnpj=cnpj,
                                operadora_id=operadora.id,
                                filtro=filtro,
                                servico=servico,
                                dados_sat=dados_sat_final,
                                unidade=unidade,
                                login_portal=login,
                                senha_portal=senha,
                                cpf=cpf,
                                status_ativo=True
                            )
                            db.session.add(cliente)
                            sucesso += 1
                            
                            if total % 50 == 0:
                                print(f"   ✅ Linha {idx}: {razao_social[:40]} - IMPORTADO")
                        
                        if total % 50 == 0:
                            db.session.commit()
                            print(f"   💾 Salvando lote... ({total} processados)")
                        
                    except Exception as e:
                        print(f"   ❌ Linha {idx}: Erro - {str(e)}")
                        erros += 1
                        db.session.rollback()
                        continue
                
                db.session.commit()
                print()
                print("=" * 80)
                print("RESUMO DA IMPORTAÇÃO")
                print("=" * 80)
                print(f"Total de linhas processadas: {total}")
                print(f"✅ Novos clientes criados:   {sucesso}")
                print(f"🔄 Clientes atualizados:     {atualizados}")
                print(f"❌ Erros encontrados:        {erros}")
                print("=" * 80)
                
        except Exception as e:
            print(f"\n❌ Erro fatal na importação: {str(e)}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    csv_path = 'attached_assets/DADOS SAT - BGTELECOM - BGTELECOM _1749158134409_1762289220985.csv'
    importar_clientes(csv_path)
