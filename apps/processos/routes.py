import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from sqlalchemy import and_, or_, desc
from sqlalchemy.orm import joinedload

from . import bp
from .forms import ProcessoForm, ProcessoFiltroForm, AprovacaoForm, CriarProcessosMensaisForm
from apps import db
from apps.models import Processo, Cliente, Operadora, Execucao, Usuario, StatusProcesso
from apps.authentication.util import verify_user_jwt

logger = logging.getLogger(__name__)

@dataclass
class ProcessoFiltros:
    """Classe para organizar filtros de processos"""
    busca: Optional[str] = None
    status: Optional[str] = None
    mes_ano: Optional[str] = None
    operadora_id: Optional[str] = None

    @classmethod
    def from_request_args(cls, args) -> 'ProcessoFiltros':
        """Cria instância a partir dos argumentos da requisição"""
        return cls(
            busca=args.get('busca', '').strip() or None,
            status=args.get('status', '').strip() or None,
            mes_ano=args.get('mes_ano', '').strip() or None,
            operadora_id=args.get('operadora', '').strip() or None
        )

class ProcessoService:
    """Serviço para operações com processos"""

    @staticmethod
    def buscar_clientes_por_termo(termo: str) -> List[int]:
        """Busca IDs de clientes por termo de pesquisa"""
        cliente_ids = set()

        # Buscar clientes por nome/cnpj
        clientes_encontrados = Cliente.query.filter(
            or_(
                Cliente.razao_social.like(f'%{termo}%'),
                Cliente.nome_sat.like(f'%{termo}%'),
                Cliente.cnpj.like(f'%{termo}%')
            )
        ).all()

        for cliente in clientes_encontrados:
            cliente_ids.add(cliente.id)

        # Buscar clientes por operadora
        operadoras_encontradas = Operadora.query.filter(
            Operadora.nome.like(f'%{termo}%')
        ).all()

        for operadora in operadoras_encontradas:
            clientes_op = Cliente.query.filter_by(operadora_id=operadora.id).all()
            for cliente in clientes_op:
                cliente_ids.add(cliente.id)

        return list(cliente_ids)

    @staticmethod
    def aplicar_filtros(query, filtros: ProcessoFiltros):
        """Aplica filtros à query de processos"""

        if filtros.busca:
            cliente_ids = ProcessoService.buscar_clientes_por_termo(filtros.busca)
            if cliente_ids:
                query = query.filter(Processo.cliente_id.in_(cliente_ids))
            else:
                # Retorna query vazia se nenhum cliente foi encontrado
                query = query.filter(Processo.id.is_(None))

        if filtros.status:
            query = query.filter(Processo.status_processo == filtros.status)

        if filtros.mes_ano:
            query = query.filter(Processo.mes_ano == filtros.mes_ano)

        if filtros.operadora_id:
            clientes_da_operadora = Cliente.query.filter_by(
                operadora_id=filtros.operadora_id
            ).all()

            if clientes_da_operadora:
                operadora_cliente_ids = [c.id for c in clientes_da_operadora]
                query = query.filter(Processo.cliente_id.in_(operadora_cliente_ids))
            else:
                query = query.filter(Processo.id.is_(None))

        return query

@bp.route('/')
@verify_user_jwt
def index():
    """Lista todos os processos com filtros e paginação"""
    try:
        # Paginação
        page = request.args.get('page', 1, type=int)
        per_page = 10

        # Parâmetros de filtro
        filtros = ProcessoFiltros.from_request_args(request.args)

        # Query inicial
        query = Processo.query

        # Aplicar filtros
        query = ProcessoService.aplicar_filtros(query, filtros)

        # Ordenação
        query = query.order_by(Processo.data_atualizacao.desc())

        # Paginação
        processos = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        form = ProcessoFiltroForm(request.args)

        return render_template(
            'processos/index.html',
            processos=processos,
            form=form
        )

    except Exception as e:
        logger.error("Erro ao carregar processos: %s", str(e))
        flash('Erro ao carregar processos. Tente novamente.', 'danger')
        return redirect(url_for('home_blueprint.index'))

@bp.route('/novo', methods=['GET', 'POST'])
@verify_user_jwt
def novo():
    """Criar novo processo"""

    form = ProcessoForm()

    if form.validate_on_submit():
        try:
            if not Processo.validar_formato_mes_ano(form.mes_ano.data):
                flash('Formato de mês/ano inválido. Use MM/AAAA.', 'danger')
                return render_template('processos/form.html', form=form, titulo="Novo Processo")

            # Verificar duplicatas
            processo_existente = db.session.query(Processo).filter(
                and_(
                    Processo.cliente_id == form.cliente_id.data,
                    Processo.mes_ano == form.mes_ano.data
                )
            ).first()

            if processo_existente:
                flash('Já existe um processo para este cliente no mês/ano informado.', 'danger')
                return render_template('processos/form.html', form=form, titulo="Novo Processo")

            # Criar processo
            processo = Processo(
                cliente_id=form.cliente_id.data,
                mes_ano=form.mes_ano.data,
                status_processo=form.status_processo.data,
                url_fatura=form.url_fatura.data or None,
                data_vencimento=form.data_vencimento.data,
                valor_fatura=form.valor_fatura.data,
                upload_manual=form.upload_manual.data,
                criado_automaticamente=form.criado_automaticamente.data,
                observacoes=form.observacoes.data or None
            )

            db.session.add(processo)
            db.session.commit()

            logger.info("Processo criado: %s - %s - %s", processo.id, processo.cliente.razao_social, processo.mes_ano)
            flash('Processo criado com sucesso!', 'success')

            return redirect(url_for('processos_bp.visualizar', id=processo.id))

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar processo: %s", str(e))
            flash('Erro ao criar processo. Tente novamente.', 'danger')

    return render_template('processos/form.html', form=form, titulo="Novo Processo")

@bp.route('/visualizar/<id>')
@verify_user_jwt
def visualizar(id):
    """Visualizar detalhes de um processo"""

    processo = db.session.query(Processo)\
        .options(
            joinedload(Processo.cliente).joinedload(Cliente.operadora),
            joinedload(Processo.aprovador)
        )\
        .filter(Processo.id == id)\
        .first_or_404()

    execucoes = db.session.query(Execucao)\
        .filter(Execucao.processo_id == id)\
        .order_by(desc(Execucao.data_inicio))\
        .all()

    return render_template(
        'processos/detalhes.html',
        processo=processo,
        execucoes=execucoes
    )

@bp.route('/editar/<id>', methods=['GET', 'POST'])
@verify_user_jwt
def editar(id):
    """Editar processo existente"""

    processo = db.session.query(Processo).filter(Processo.id == id).first_or_404()
    form = ProcessoForm(obj=processo)

    if form.validate_on_submit():
        try:
            if not Processo.validar_formato_mes_ano(form.mes_ano.data):
                flash('Formato de mês/ano inválido. Use MM/AAAA.', 'danger')
                return render_template('processos/form.html', form=form, titulo="Editar Processo")

            # Verificar duplicatas (excluindo o processo atual)
            if (form.cliente_id.data != str(processo.cliente_id) or 
                form.mes_ano.data != processo.mes_ano):

                processo_existente = db.session.query(Processo).filter(
                    and_(
                        Processo.cliente_id == form.cliente_id.data,
                        Processo.mes_ano == form.mes_ano.data,
                        Processo.id != id
                    )
                ).first()

                if processo_existente:
                    flash('Já existe um processo para este cliente no mês/ano informado.', 'danger')
                    return render_template('processos/form.html', form=form, titulo="Editar Processo")

            # Atualizar processo
            processo.cliente_id = form.cliente_id.data
            processo.mes_ano = form.mes_ano.data
            processo.status_processo = form.status_processo.data
            processo.url_fatura = form.url_fatura.data or None
            processo.data_vencimento = form.data_vencimento.data
            processo.valor_fatura = form.valor_fatura.data
            processo.upload_manual = form.upload_manual.data
            processo.criado_automaticamente = form.criado_automaticamente.data
            processo.observacoes = form.observacoes.data or None

            db.session.commit()

            logger.info("Processo atualizado: %s", processo.id)
            flash('Processo atualizado com sucesso!', 'success')

            return redirect(url_for('processos_bp.visualizar', id=processo.id))

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao atualizar processo: %s", str(e))
            flash('Erro ao atualizar processo. Tente novamente.', 'danger')

    return render_template('processos/form.html', form=form, titulo="Editar Processo")

@bp.route('/excluir/<id>', methods=['POST'])
@verify_user_jwt
def excluir(id):
    """Excluir processo"""

    try:
        processo = db.session.query(Processo).filter(Processo.id == id).first_or_404()

        status_protegidos = [
            StatusProcesso.APROVADO.value,
            StatusProcesso.ENVIADO_SAT.value,
            StatusProcesso.CONCLUIDO.value
        ]

        if processo.status_processo in status_protegidos:
            flash('Não é possível excluir processos aprovados ou concluídos.', 'warning')
            return redirect(url_for('processos_bp.visualizar', id=id))

        cliente_nome = processo.cliente.razao_social
        mes_ano = processo.mes_ano

        db.session.delete(processo)
        db.session.commit()

        logger.info("Processo excluído: %s - %s - %s", id, cliente_nome, mes_ano)
        flash('Processo excluído com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        logger.error("Erro ao excluir processo %s: %s", id, str(e))
        flash('Erro ao excluir processo.', 'danger')

    return redirect(url_for('processos_bp.index'))

@bp.route('/aprovar/<string:id>', methods=['POST'])
@verify_user_jwt
def aprovar(id):
    """Aprovar processo"""

    try:
        processo = db.session.query(Processo).filter(Processo.id == id).first_or_404()

        if not processo.pode_ser_aprovado:
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'success': False,
                    'message': 'Processo não pode ser aprovado no status atual.'
                }), 400
            else:
                flash('Este processo não pode ser aprovado no status atual.', 'warning')
                return redirect(url_for('processos_bp.visualizar', id=id))

        observacoes = None
        if request.is_json:
            data = request.get_json()
            observacoes = data.get('observacoes', '').strip() if data else ''
        else:
            observacoes = request.form.get('observacoes', '').strip()

        usuario_id = "00000000-0000-0000-0000-000000000000"
        processo.aprovar(usuario_id, observacoes)

        db.session.commit()

        logger.info("Processo aprovado: %s", processo.id)

        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                'success': True,
                'message': 'Fatura aprovada com sucesso!'
            })
        else:
            flash('Processo aprovado com sucesso!', 'success')
            return redirect(url_for('processos_bp.visualizar', id=id))

    except Exception as e:
        db.session.rollback()
        logger.error("Erro ao aprovar processo %s: %s", id, str(e))

        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                'success': False,
                'message': 'Erro interno do servidor.'
            }), 500
        else:
            flash('Erro ao aprovar processo.', 'danger')
            return redirect(url_for('processos_bp.visualizar', id=id))

@bp.route('/rejeitar/<string:id>', methods=['POST'])
@verify_user_jwt
def rejeitar(id):
    """Rejeitar processo"""

    try:
        processo = db.session.query(Processo).filter(Processo.id == id).first_or_404()

        observacoes = None
        if request.is_json:
            data = request.get_json()
            observacoes = data.get('observacoes', '').strip() if data else ''
        else:
            observacoes = request.form.get('observacoes', '').strip()

        if not observacoes:
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'success': False,
                    'message': 'Motivo da rejeição é obrigatório.'
                }), 400
            else:
                flash('Motivo da rejeição é obrigatório.', 'warning')
                return redirect(url_for('processos_bp.visualizar', id=id))

        if not processo.esta_pendente_aprovacao:
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'success': False,
                    'message': 'Este processo não está pendente de aprovação.'
                }), 400
            else:
                flash('Este processo não está pendente de aprovação.', 'warning')
                return redirect(url_for('processos_bp.visualizar', id=id))

        processo.rejeitar(observacoes)

        db.session.commit()

        logger.info("Processo rejeitado: %s", processo.id)

        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                'success': True,
                'message': 'Fatura rejeitada com sucesso!'
            })
        else:
            flash('Processo rejeitado.', 'info')
            return redirect(url_for('processos_bp.visualizar', id=id))

    except Exception as e:
        db.session.rollback()
        logger.error("Erro ao rejeitar processo %s: %s", id, str(e))

        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                'success': False,
                'message': 'Erro interno do servidor.'
            }), 500
        else:
            flash('Erro ao rejeitar processo.', 'danger')
            return redirect(url_for('processos_bp.visualizar', id=id))

@bp.route('/criar-processos-mensais', methods=['GET', 'POST'])
@verify_user_jwt
def criar_processos_mensais():
    """Criar processos mensais automaticamente para todos os clientes ativos"""

    form = CriarProcessosMensaisForm()

    if form.validate_on_submit():
        try:
            if not Processo.validar_formato_mes_ano(form.mes_ano.data):
                flash('Formato de mês/ano inválido. Use MM/AAAA.', 'danger')
                return render_template('processos/criar_mensais.html', form=form)

            query_clientes = db.session.query(Cliente)\
                .join(Operadora)\
                .filter(
                    Cliente.status_ativo == True,
                    Operadora.status_ativo == True
                )

            if form.operadora_id.data:
                query_clientes = query_clientes.filter(Cliente.operadora_id == form.operadora_id.data)

            clientes = query_clientes.all()

            processos_criados = 0
            processos_ja_existentes = 0

            for cliente in clientes:
                processo_existente = db.session.query(Processo).filter(
                    and_(
                        Processo.cliente_id == cliente.id,
                        Processo.mes_ano == form.mes_ano.data
                    )
                ).first()

                if processo_existente:
                    processos_ja_existentes += 1
                    continue

                processo = Processo(
                    cliente_id=cliente.id,
                    mes_ano=form.mes_ano.data,
                    status_processo=StatusProcesso.AGUARDANDO_DOWNLOAD.value,
                    criado_automaticamente=True
                )

                db.session.add(processo)
                processos_criados += 1

            db.session.commit()

            logger.info("Processos mensais criados: %s para %s", processos_criados, form.mes_ano.data)

            if processos_criados > 0:
                flash(f'Criados {processos_criados} processos para {form.mes_ano.data}!', 'success')

            if processos_ja_existentes > 0:
                flash(f'{processos_ja_existentes} processos já existiam para este período.', 'info')

            if processos_criados == 0 and processos_ja_existentes == 0:
                flash('Nenhum cliente ativo encontrado.', 'warning')

            return redirect(url_for('processos_bp.index'))

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar processos mensais: %s", str(e))
            flash('Erro ao criar processos mensais.', 'danger')

    return render_template('processos/criar_mensais.html', form=form)

@bp.route('/enviar-sat/<string:id>', methods=['POST'])
@verify_user_jwt
def enviar_sat(id):
    """Envia processo para o SAT (mock por enquanto)"""

    try:
        processo = db.session.query(Processo).filter(Processo.id == id).first_or_404()

        if not processo.pode_enviar_sat:
            return jsonify({
                'success': False,
                'message': 'Este processo não pode ser enviado para o SAT no status atual.'
            }), 400

        processo.enviar_para_sat()

        db.session.commit()

        logger.info("Processo enviado para SAT (mock): %s", processo.id)

        return jsonify({
            'success': True,
            'message': 'Fatura enviada para o SAT com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        logger.error("Erro ao enviar processo %s para SAT: %s", id, str(e))
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor.'
        }), 500

@bp.route('/api/estatisticas')
@verify_user_jwt
def api_estatisticas():
    """API para estatísticas do dashboard"""

    try:
        total_processos = db.session.query(Processo).count()

        status_counts = {}
        for status in StatusProcesso:
            count = db.session.query(Processo)\
                .filter(Processo.status_processo == status.value)\
                .count()
            status_counts[status.value] = count

        pendentes_aprovacao = db.session.query(Processo)\
            .filter(Processo.status_processo == StatusProcesso.DOWNLOAD_COMPLETO.value)\
            .count()

        mes_atual = Processo.criar_mes_ano_atual()
        processos_mes_atual = db.session.query(Processo)\
            .filter(Processo.mes_ano == mes_atual)\
            .count()

        return jsonify({
            'total_processos': total_processos,
            'status_counts': status_counts,
            'pendentes_aprovacao': pendentes_aprovacao,
            'processos_mes_atual': processos_mes_atual
        })

    except Exception as e:
        logger.error("Erro ao buscar estatísticas: %s", str(e))
        return jsonify({'error': 'Erro interno'}), 500