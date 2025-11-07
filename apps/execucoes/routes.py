"""
Rotas do módulo de Execuções
"""

import logging
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

from . import bp
from .forms import ExecucaoFiltroForm
from .services import ExecucaoService, ExecucaoFiltros
from apps import db
from apps.models import Execucao, Processo, Cliente, Operadora
from apps.models.execucao import StatusExecucao

logger = logging.getLogger(__name__)


@bp.route('/')
@login_required
def index():
    """Lista todas as execuções com filtros e paginação"""
    try:
        logger.info("=== INICIANDO ROTA INDEX EXECUÇÕES ===")
        
        # Paginação
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Filtros
        filtros = ExecucaoFiltros.from_request_args(request.args)
        
        # Query base
        query = Execucao.query.options(
            joinedload(Execucao.processo).joinedload(Processo.cliente).joinedload(Cliente.operadora),
            joinedload(Execucao.executor)
        )
        
        # Aplica filtros
        query = ExecucaoService.aplicar_filtros(query, filtros)
        
        # Ordenação
        query = query.order_by(desc(Execucao.data_inicio))
        
        # Paginação
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Formulário de filtros
        form = ExecucaoFiltroForm(request.args)
        
        # Popula operadoras no formulário
        operadoras = Operadora.query.order_by(Operadora.nome).all()
        form.operadora.choices = [('', 'Todas as operadoras')] + [
            (str(op.id), op.nome) for op in operadoras
        ]
        
        # Estatísticas
        stats = ExecucaoService.obter_estatisticas(filtros)
        
        logger.info(f"Execuções carregadas: {pagination.total} total, página {page}")
        
        return render_template(
            'execucoes/index.html',
            execucoes=pagination.items,
            pagination=pagination,
            form=form,
            stats=stats,
            filtros=filtros
        )
        
    except Exception as e:
        logger.error(f"Erro na rota index de execuções: {e}", exc_info=True)
        flash('Erro ao carregar execuções', 'error')
        return redirect(url_for('home_blueprint.index'))


@bp.route('/detalhes/<string:execucao_id>')
@login_required
def detalhes(execucao_id):
    """Exibe detalhes de uma execução específica"""
    try:
        logger.info(f"Carregando detalhes da execução {execucao_id}")
        
        execucao = Execucao.query.options(
            joinedload(Execucao.processo).joinedload(Processo.cliente).joinedload(Cliente.operadora),
            joinedload(Execucao.executor)
        ).get(execucao_id)
        
        if not execucao:
            flash('Execução não encontrada', 'error')
            return redirect(url_for('execucoes_bp.index'))
        
        # Busca outras execuções do mesmo processo
        outras_execucoes = Execucao.query.filter(
            Execucao.processo_id == execucao.processo_id,
            Execucao.id != execucao.id
        ).order_by(desc(Execucao.data_inicio)).limit(5).all()
        
        return render_template(
            'execucoes/detalhes.html',
            execucao=execucao,
            outras_execucoes=outras_execucoes
        )
        
    except Exception as e:
        logger.error(f"Erro ao carregar detalhes da execução: {e}", exc_info=True)
        flash('Erro ao carregar detalhes da execução', 'error')
        return redirect(url_for('execucoes_bp.index'))


@bp.route('/retentar/<string:execucao_id>', methods=['POST'])
@login_required
def retentar(execucao_id):
    """Retenta uma execução que falhou"""
    try:
        logger.info(f"Retentando execução {execucao_id}")
        
        execucao = Execucao.query.get(execucao_id)
        
        if not execucao:
            return jsonify({'success': False, 'message': 'Execução não encontrada'}), 404
        
        if not execucao.falhou:
            return jsonify({
                'success': False,
                'message': 'Apenas execuções falhadas podem ser retentadas'
            }), 400
        
        # Cria nova tentativa
        nova_execucao = ExecucaoService.retentar_execucao(
            execucao_id=execucao_id,
            usuario_id=current_user.id
        )
        
        flash(f'Nova tentativa criada com sucesso (Tentativa #{nova_execucao.numero_tentativa})', 'success')
        
        return jsonify({
            'success': True,
            'message': 'Execução retentada com sucesso',
            'nova_execucao_id': str(nova_execucao.id),
            'redirect_url': url_for('execucoes_bp.detalhes', execucao_id=nova_execucao.id)
        })
        
    except Exception as e:
        logger.error(f"Erro ao retentar execução: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/estatisticas')
@login_required
def estatisticas():
    """Retorna estatísticas das execuções em JSON"""
    try:
        filtros = ExecucaoFiltros.from_request_args(request.args)
        stats = ExecucaoService.obter_estatisticas(filtros)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.route('/cancelar/<string:execucao_id>', methods=['POST'])
@login_required
def cancelar(execucao_id):
    """Cancela uma execução em andamento"""
    try:
        logger.info(f"Cancelando execução {execucao_id}")
        
        execucao = Execucao.query.get(execucao_id)
        
        if not execucao:
            return jsonify({'success': False, 'message': 'Execução não encontrada'}), 404
        
        if not execucao.esta_em_andamento:
            return jsonify({
                'success': False,
                'message': 'Apenas execuções em andamento podem ser canceladas'
            }), 400
        
        # Cancela execução
        motivo = request.json.get('motivo', 'Cancelado pelo usuário')
        execucao.cancelar(motivo=motivo)
        db.session.commit()
        
        flash('Execução cancelada com sucesso', 'success')
        
        return jsonify({
            'success': True,
            'message': 'Execução cancelada com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao cancelar execução: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
