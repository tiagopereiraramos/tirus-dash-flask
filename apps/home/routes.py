# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps.home import blueprint
from flask import render_template, request, Blueprint
from flask_login import login_required
from jinja2 import TemplateNotFound
from sqlalchemy import func
from apps import db
from apps.models import Processo, Cliente, Operadora
from apps.models.processo import StatusProcesso
import logging

logger = logging.getLogger(__name__)

# Blueprint específico para home
home_bp = Blueprint('home_bp', __name__, url_prefix='/home')


@blueprint.route('/')
@blueprint.route('/index')
@login_required  
def index():
    try:
        logger.info("Iniciando carregamento do dashboard")
        
        # Calcular métricas básicas
        logger.debug("Calculando métricas básicas")
        total_processos = db.session.query(Processo).count()
        logger.debug(f"Total de processos: {total_processos}")
        
        # Verificar se os enums estão funcionando corretamente
        try:
            status_aguardando = StatusProcesso.AGUARDANDO_DOWNLOAD.value
            status_download = StatusProcesso.DOWNLOAD_CONCLUIDO.value  
            status_pendente = StatusProcesso.PENDENTE_APROVACAO.value
            status_aprovado = StatusProcesso.APROVADO.value
            
            logger.debug(f"Status enum values: {status_aguardando}, {status_download}, {status_pendente}, {status_aprovado}")
        except Exception as enum_error:
            logger.error(f"Erro com enums: {enum_error}")
            # Usar valores hardcoded como fallback
            status_aguardando = 'AGUARDANDO_DOWNLOAD'
            status_download = 'DOWNLOAD_CONCLUIDO'
            status_pendente = 'PENDENTE_APROVACAO'
            status_aprovado = 'APROVADO'
        
        processos_ativos = db.session.query(Processo).filter(
            Processo.status_processo.in_([
                status_aguardando,
                status_download,
                status_pendente
            ])
        ).count()
        logger.debug(f"Processos ativos: {processos_ativos}")
        
        aguardando_aprovacao = db.session.query(Processo).filter_by(
            status_processo=status_pendente
        ).count()
        logger.debug(f"Aguardando aprovação: {aguardando_aprovacao}")
        
        aprovados = db.session.query(Processo).filter_by(
            status_processo=status_aprovado
        ).count()
        logger.debug(f"Aprovados: {aprovados}")
        
        total_clientes = db.session.query(Cliente).filter_by(status_ativo=True).count()
        logger.debug(f"Total clientes: {total_clientes}")
        
        # Processos recentes - simplificado
        logger.debug("Buscando processos recentes")
        try:
            processos_recentes = db.session.query(Processo)\
                .join(Cliente)\
                .order_by(Processo.data_atualizacao.desc())\
                .limit(10).all()
            logger.debug(f"Processos recentes encontrados: {len(processos_recentes)}")
        except Exception as proc_error:
            logger.error(f"Erro ao buscar processos recentes: {proc_error}")
            processos_recentes = []
        
        # Resumo por status - simplificado
        logger.debug("Calculando resumo por status")
        try:
            status_counts = db.session.query(
                Processo.status_processo,
                func.count(Processo.id).label('quantidade')
            ).group_by(Processo.status_processo).all()
            
            resumo_status = []
            total_for_percentage = sum([s.quantidade for s in status_counts])
            
            status_mapping = {
                'AGUARDANDO_DOWNLOAD': {'nome': 'Aguardando Download', 'cor': 'warning'},
                'DOWNLOAD_CONCLUIDO': {'nome': 'Download Concluído', 'cor': 'info'},
                'PENDENTE_APROVACAO': {'nome': 'Pendente Aprovação', 'cor': 'orange'},
                'APROVADO': {'nome': 'Aprovado', 'cor': 'green'},
                'REJEITADO': {'nome': 'Rejeitado', 'cor': 'red'},
                'ENVIADO_SAT': {'nome': 'Enviado SAT', 'cor': 'blue'}
            }
            
            for status in status_counts:
                if status.status_processo in status_mapping:
                    info = status_mapping[status.status_processo]
                    percentual = (status.quantidade / total_for_percentage * 100) if total_for_percentage > 0 else 0
                    resumo_status.append({
                        'nome': info['nome'],
                        'quantidade': status.quantidade,
                        'cor': info['cor'],
                        'percentual': round(percentual, 1)
                    })
            logger.debug(f"Resumo status calculado: {len(resumo_status)} itens")
        except Exception as status_error:
            logger.error(f"Erro ao calcular resumo por status: {status_error}")
            resumo_status = []
        
        # Resumo por operadora - simplificado  
        logger.debug("Calculando resumo por operadora")
        try:
            operadoras_data = db.session.query(
                Operadora.nome,
                func.count(Processo.id).label('total_processos')
            ).join(Cliente).join(Processo)\
             .group_by(Operadora.id, Operadora.nome)\
             .order_by(func.count(Processo.id).desc())\
             .limit(6).all()
            
            operadoras_resumo = []
            for op in operadoras_data:
                operadoras_resumo.append({
                    'nome': op.nome,
                    'total_processos': op.total_processos,
                    'aprovados': 0,  # Simplificado por enquanto
                    'pendentes': 0   # Simplificado por enquanto
                })
            logger.debug(f"Resumo operadoras calculado: {len(operadoras_resumo)} itens")
        except Exception as op_error:
            logger.error(f"Erro ao calcular resumo por operadora: {op_error}")
            operadoras_resumo = []
        
        metricas = {
            'total_processos': total_processos,
            'processos_ativos': processos_ativos,
            'aguardando_aprovacao': aguardando_aprovacao,
            'aprovados': aprovados,
            'total_clientes': total_clientes
        }
        
        logger.info("Dashboard carregado com sucesso")
        logger.debug(f"Métricas finais: {metricas}")
        
        return render_template('home/index.html', 
                             segment='index',
                             metricas=metricas,
                             processos_recentes=processos_recentes,
                             resumo_status=resumo_status,
                             operadoras_resumo=operadoras_resumo)
    
    except Exception as e:
        logger.error(f"Erro geral no dashboard: {e}")
        logger.error(f"Tipo do erro: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Em caso de erro, renderizar dashboard básico
        metricas = {
            'total_processos': 0,
            'processos_ativos': 0,
            'aguardando_aprovacao': 0,
            'aprovados': 0,
            'total_clientes': 0
        }
        return render_template('home/index.html', 
                             segment='index',
                             metricas=metricas,
                             processos_recentes=[],
                             resumo_status=[],
                             operadoras_resumo=[])

@blueprint.route('/<template>')
@login_required
def route_template(template):
    try:
        if not template.endswith('.html'):
            template += '.html'
        
        # Detect the current page
        segment = get_segment(request)
        
        # Serve the file (if exists) from app/templates/home/FILE.html
        return render_template("home/" + template, segment=segment)
    
    except TemplateNotFound:
        return render_template('home/page-404.html'), 404
    
    except:
        return render_template('home/page-500.html'), 500

# Rotas para o blueprint home_bp
@home_bp.route('/')
@home_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('home/index.html', segment='dashboard')

@home_bp.route('/index')
@login_required
def index():
    return render_template('home/index.html', segment='index')

@home_bp.route('/index')
@login_required
def home_index():
    return render_template('home/index.html', segment='index')


# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment

    except:
        return None
