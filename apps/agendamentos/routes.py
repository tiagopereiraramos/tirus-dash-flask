"""
Rotas para gerenciamento de agendamentos
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, desc
from datetime import datetime, timedelta
import json
import logging

from apps import db
from apps.models import Agendamento, TipoAgendamento, Operadora
from apps.agendamentos.forms import AgendamentoForm, FiltroAgendamentoForm, CronHelper

logger = logging.getLogger(__name__)

# Criar o blueprint
agendamentos_bp = Blueprint('agendamentos', __name__)


@agendamentos_bp.route('/')
@login_required
def index():
    """Lista todos os agendamentos com filtros e paginação"""
    try:
        # Paginação
        page = request.args.get('page', 1, type=int)
        per_page = 10

        # Query inicial
        query = Agendamento.query

        # Aplicar filtros
        if request.args.get('nome'):
            query = query.filter(
                Agendamento.nome_agendamento.ilike(
                    f"%{request.args.get('nome')}%")
            )

        if request.args.get('tipo'):
            query = query.filter(
                Agendamento.tipo_agendamento == request.args.get('tipo'))

        if request.args.get('operadora'):
            query = query.filter(Agendamento.operadora_id ==
                                 request.args.get('operadora'))

        if request.args.get('status'):
            if request.args.get('status') == 'ativo':
                query = query.filter(Agendamento.status_ativo == True)
            elif request.args.get('status') == 'inativo':
                query = query.filter(Agendamento.status_ativo == False)

        # Ordenação
        query = query.order_by(Agendamento.data_criacao.desc())

        # Paginação
        agendamentos = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        # Calcular estatísticas
        total_agendamentos = Agendamento.query.count()
        agendamentos_ativos = Agendamento.query.filter_by(
            status_ativo=True).count()
        agendamentos_inativos = total_agendamentos - agendamentos_ativos

        # Agendamentos por tipo
        agendamentos_por_tipo = {}
        for tipo in TipoAgendamento:
            count = Agendamento.query.filter_by(
                tipo_agendamento=tipo.value).count()
            agendamentos_por_tipo[tipo.value] = count

        # Formulário de filtros
        form = FiltroAgendamentoForm(request.args)

        # Buscar operadoras para o filtro
        operadoras = Operadora.query.filter_by(
            status_ativo=True).order_by(Operadora.nome).all()

        # Gerar CSRF token para JavaScript
        from flask_wtf.csrf import generate_csrf
        csrf_token = generate_csrf()

        return render_template('agendamentos/index.html',
                               agendamentos=agendamentos,
                               form=form,
                               operadoras=operadoras,
                               total_agendamentos=total_agendamentos,
                               agendamentos_ativos=agendamentos_ativos,
                               agendamentos_inativos=agendamentos_inativos,
                               agendamentos_por_tipo=agendamentos_por_tipo,
                               csrf_token=csrf_token)

    except Exception as e:
        logger.error(f"Erro ao listar agendamentos: {e}")
        flash('Erro ao carregar agendamentos', 'error')
        from flask_wtf.csrf import generate_csrf
        csrf_token = generate_csrf()
        return render_template('agendamentos/index.html',
                               agendamentos=None,
                               form=FiltroAgendamentoForm(),
                               total_agendamentos=0,
                               agendamentos_ativos=0,
                               agendamentos_inativos=0,
                               agendamentos_por_tipo={},
                               csrf_token=csrf_token)


@agendamentos_bp.route('/teste', methods=['GET'])
@login_required
def teste():
    """Rota de teste com formulário simples"""
    from flask_wtf.csrf import generate_csrf
    csrf_token = generate_csrf()
    return render_template('teste_formulario_simples.html', csrf_token=csrf_token)


@agendamentos_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    """Criar novo agendamento"""
    logger.info("=== ROTA NOVO AGENDAMENTO CHAMADA ===")
    logger.info(f"Método HTTP: {request.method}")
    logger.info(f"URL: {request.url}")

    form = AgendamentoForm()

    logger.info(f"Formulário submetido: {form.is_submitted()}")
    logger.info(f"Formulário válido: {form.validate()}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request form data: {dict(request.form)}")

    if form.is_submitted():
        logger.info("=== FORMULÁRIO FOI SUBMETIDO ===")
        logger.info(f"Dados do formulário:")
        logger.info(f"  Nome: {form.nome_agendamento.data}")
        logger.info(f"  Descrição: {form.descricao.data}")
        logger.info(f"  Tipo: {form.tipo_agendamento.data}")
        logger.info(f"  Operadora: {form.operadora.data}")
        logger.info(f"  Frequência: {form.frequencia.data}")
        logger.info(f"  Hora: {form.hora.data}")
        logger.info(f"  Minuto: {form.minuto.data}")
        logger.info(f"  Dia semana: {form.dia_semana.data}")
        logger.info(f"  Dia mês: {form.dia_mes.data}")
        logger.info(f"  Cron: {form.cron_expressao.data}")
        logger.info(f"  Status: {form.status_ativo.data}")

        if not form.validate():
            logger.error(f"Erros de validação: {form.errors}")
            logger.error("Formulário inválido - não será processado")
        else:
            logger.info("Formulário válido - será processado")

    if form.validate_on_submit():
        logger.info("=== VALIDATE_ON_SUBMIT PASSOU - CRIANDO AGENDAMENTO ===")
        try:
            # Criar parâmetros de execução baseados no tipo
            parametros = {}
            if form.tipo_agendamento.data == 'EXECUTAR_DOWNLOADS':
                parametros = {
                    'apenas_processos_pendentes': True,
                    'limite_execucoes_simultaneas': 5
                }
            elif form.tipo_agendamento.data == 'ENVIAR_RELATORIOS':
                parametros = {
                    'tipo_relatorio': 'semanal',
                    'incluir_graficos': True,
                    'destinatarios': ['admin@begtelecomunicacoes.com.br']
                }

            logger.info(f"Parâmetros de execução: {parametros}")

            agendamento = Agendamento(
                nome_agendamento=form.nome_agendamento.data,
                descricao=form.descricao.data,
                cron_expressao=form.cron_expressao.data,
                tipo_agendamento=form.tipo_agendamento.data,
                status_ativo=form.status_ativo.data,
                operadora_id=form.operadora.data if form.operadora.data else None,
                parametros_execucao=parametros
            )

            logger.info(f"Objeto Agendamento criado: {agendamento}")

            db.session.add(agendamento)
            logger.info("Agendamento adicionado à sessão")

            db.session.commit()
            logger.info("Commit realizado com sucesso")

            logger.info(
                f"Agendamento criado com sucesso: {agendamento.nome_agendamento}")
            flash('Agendamento criado com sucesso!', 'success')
            logger.info("Redirecionando para index...")
            return redirect(url_for('agendamentos.index'))

        except Exception as e:
            logger.error(f"Erro ao criar agendamento: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()
            flash('Erro ao criar agendamento', 'error')

    logger.info("=== RENDERIZANDO TEMPLATE FORM ===")
    return render_template('agendamentos/form.html',
                           form=form,
                           titulo='Novo Agendamento')


@agendamentos_bp.route('/editar/<string:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    """Editar agendamento existente"""
    agendamento = Agendamento.query.get_or_404(id)
    form = AgendamentoForm(obj=agendamento)

    # Preencher campos amigáveis de cron baseado na expressão cron existente
    if agendamento.cron_expressao:
        cron_config = CronHelper.cron_to_frequencia(agendamento.cron_expressao)
        form.frequencia.data = cron_config.get('frequencia', 'diario')
        form.hora.data = str(cron_config.get('hora', 0))
        form.minuto.data = str(cron_config.get('minuto', 0))
        form.dia_semana.data = cron_config.get('dia_semana', '1')
        form.dia_mes.data = str(cron_config.get('dia_mes', 1))

    if form.validate_on_submit():
        try:
            # Criar parâmetros de execução baseados no tipo
            parametros = {}
            if form.tipo_agendamento.data == 'EXECUTAR_DOWNLOADS':
                parametros = {
                    'apenas_processos_pendentes': True,
                    'limite_execucoes_simultaneas': 5
                }
            elif form.tipo_agendamento.data == 'ENVIAR_RELATORIOS':
                parametros = {
                    'tipo_relatorio': 'semanal',
                    'incluir_graficos': True,
                    'destinatarios': ['admin@begtelecomunicacoes.com.br']
                }

            agendamento.nome_agendamento = form.nome_agendamento.data
            agendamento.descricao = form.descricao.data
            agendamento.cron_expressao = form.cron_expressao.data
            agendamento.tipo_agendamento = form.tipo_agendamento.data
            agendamento.status_ativo = form.status_ativo.data
            agendamento.operadora_id = form.operadora.data if form.operadora.data else None
            agendamento.parametros_execucao = parametros

            db.session.commit()
            flash('Agendamento atualizado com sucesso!', 'success')
            return redirect(url_for('agendamentos.index'))

        except Exception as e:
            logger.error(f"Erro ao atualizar agendamento: {e}")
            db.session.rollback()
            flash('Erro ao atualizar agendamento', 'error')

    return render_template('agendamentos/form.html',
                           form=form,
                           titulo='Editar Agendamento',
                           agendamento=agendamento)


@agendamentos_bp.route('/detalhes/<string:id>')
@login_required
def detalhes(id):
    """Visualizar detalhes do agendamento"""
    agendamento = Agendamento.query.get_or_404(id)

    # Calcular estatísticas
    estatisticas = {
        'total_execucoes': 0,
        'execucoes_sucesso': 0,
        'execucoes_falha': 0,
        'ultima_execucao': agendamento.ultima_execucao,
        'proxima_execucao': agendamento.proxima_execucao
    }

    # Verificar se deve executar agora
    deve_executar_agora = agendamento.deve_executar_agora if agendamento else False

    # Gerar CSRF token para JavaScript
    from flask_wtf.csrf import generate_csrf
    csrf_token = generate_csrf()

    return render_template('agendamentos/detalhes.html',
                           agendamento=agendamento,
                           estatisticas=estatisticas,
                           deve_executar_agora=deve_executar_agora,
                           csrf_token=csrf_token)


@agendamentos_bp.route('/excluir/<string:id>', methods=['POST'])
@login_required
def excluir(id):
    """Excluir agendamento"""
    agendamento = Agendamento.query.get_or_404(id)

    try:
        db.session.delete(agendamento)
        db.session.commit()
        flash('Agendamento excluído com sucesso!', 'success')
    except Exception as e:
        logger.error(f"Erro ao excluir agendamento: {e}")
        db.session.rollback()
        flash('Erro ao excluir agendamento', 'error')

    return redirect(url_for('agendamentos.index'))


@agendamentos_bp.route('/ativar/<string:id>', methods=['POST'])
@login_required
def ativar(id):
    """Ativar agendamento"""
    agendamento = Agendamento.query.get_or_404(id)

    try:
        agendamento.ativar()
        db.session.commit()
        flash('Agendamento ativado com sucesso!', 'success')
    except Exception as e:
        logger.error(f"Erro ao ativar agendamento: {e}")
        db.session.rollback()
        flash('Erro ao ativar agendamento', 'error')

    return redirect(url_for('agendamentos.index'))


@agendamentos_bp.route('/desativar/<string:id>', methods=['POST'])
@login_required
def desativar(id):
    """Desativar agendamento"""
    agendamento = Agendamento.query.get_or_404(id)

    try:
        agendamento.desativar()
        db.session.commit()
        flash('Agendamento desativado com sucesso!', 'success')
    except Exception as e:
        logger.error(f"Erro ao desativar agendamento: {e}")
        db.session.rollback()
        flash('Erro ao desativar agendamento', 'error')

    return redirect(url_for('agendamentos.index'))


@agendamentos_bp.route('/executar-manual/<string:id>', methods=['POST'])
@login_required
def executar_manual(id):
    """Executar agendamento manualmente"""
    agendamento = Agendamento.query.get_or_404(id)

    try:
        # Aqui você implementaria a lógica de execução do agendamento
        # Por enquanto, apenas marca como executado
        agendamento.marcar_execucao()
        db.session.commit()

        flash('Agendamento executado manualmente com sucesso!', 'success')
    except Exception as e:
        logger.error(f"Erro ao executar agendamento manualmente: {e}")
        db.session.rollback()
        flash('Erro ao executar agendamento', 'error')

    return redirect(url_for('agendamentos.detalhes', id=id))


@agendamentos_bp.route('/api/status/<string:id>')
@login_required
def api_status(id):
    """API para obter status do agendamento"""
    try:
        agendamento = Agendamento.query.get_or_404(id)

        return jsonify({
            'success': True,
            'agendamento': {
                'id': str(agendamento.id),
                'nome': agendamento.nome_agendamento,
                'tipo': agendamento.tipo_agendamento,
                'status_ativo': agendamento.status_ativo,
                'ultima_execucao': agendamento.ultima_execucao.isoformat() if agendamento.ultima_execucao else None,
                'proxima_execucao': agendamento.proxima_execucao.isoformat() if agendamento.proxima_execucao else None,
                'deve_executar_agora': agendamento.deve_executar_agora
            }
        })
    except Exception as e:
        logger.error(f"Erro ao obter status do agendamento: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
