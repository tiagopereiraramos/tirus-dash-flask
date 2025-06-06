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

# Blueprint específico para home
home_bp = Blueprint('home_bp', __name__, url_prefix='/home')


@blueprint.route('/index')
@login_required
def index():
    try:
        # Calcular métricas
        total_processos = Processo.query.count()
        processos_ativos = Processo.query.filter(
            Processo.status_processo.in_([
                StatusProcesso.AGUARDANDO_DOWNLOAD.value,
                StatusProcesso.DOWNLOAD_CONCLUIDO.value,
                StatusProcesso.PENDENTE_APROVACAO.value
            ])
        ).count()
        
        aguardando_aprovacao = Processo.query.filter_by(
            status_processo=StatusProcesso.PENDENTE_APROVACAO.value
        ).count()
        
        aprovados = Processo.query.filter_by(
            status_processo=StatusProcesso.APROVADO.value
        ).count()
        
        total_clientes = Cliente.query.filter_by(status_ativo=True).count()
        
        # Processos recentes
        processos_recentes = Processo.query.join(Cliente).join(Operadora)\
            .order_by(Processo.data_atualizacao.desc())\
            .limit(10).all()
        
        # Resumo por status
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
        
        # Resumo por operadora
        operadoras_data = db.session.query(
            Operadora.nome,
            func.count(Processo.id).label('total_processos'),
            func.sum(func.case([(Processo.status_processo == StatusProcesso.APROVADO.value, 1)], else_=0)).label('aprovados'),
            func.sum(func.case([(Processo.status_processo == StatusProcesso.PENDENTE_APROVACAO.value, 1)], else_=0)).label('pendentes')
        ).join(Cliente).join(Processo)\
         .group_by(Operadora.id, Operadora.nome)\
         .order_by(func.count(Processo.id).desc())\
         .limit(6).all()
        
        operadoras_resumo = []
        for op in operadoras_data:
            operadoras_resumo.append({
                'nome': op.nome,
                'total_processos': op.total_processos,
                'aprovados': op.aprovados or 0,
                'pendentes': op.pendentes or 0
            })
        
        metricas = {
            'total_processos': total_processos,
            'processos_ativos': processos_ativos,
            'aguardando_aprovacao': aguardando_aprovacao,
            'aprovados': aprovados,
            'total_clientes': total_clientes
        }
        
        return render_template('home/index.html', 
                             segment='index',
                             metricas=metricas,
                             processos_recentes=processos_recentes,
                             resumo_status=resumo_status,
                             operadoras_resumo=operadoras_resumo)
    
    except Exception as e:
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
