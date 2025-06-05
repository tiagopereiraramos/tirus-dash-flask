import logging
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from sqlalchemy import and_, or_, desc
from sqlalchemy.orm import joinedload

from . import bp
from .forms import ProcessoForm, ProcessoFiltroForm, AprovacaoForm, CriarProcessosMensaisForm
from apps import db
from apps.models import Processo, Cliente, Operadora, Execucao, Usuario, StatusProcesso
from apps.authentication.util import verify_user_jwt

logger = logging.getLogger(__name__)


@bp.route('/')
@verify_user_jwt
def index():
    """Lista todos os processos com filtros e paginação"""

    try:
        # Query base simplificada primeiro
        query = db.session.query(Processo)

        # Aplicar filtros simples dos parâmetros da URL
        busca = request.args.get('busca', '')
        status = request.args.get('status', '')
        mes_ano = request.args.get('mes_ano', '')
        operadora_id = request.args.get('operadora', '')

        if busca:
            busca_term = f"%{busca}%"
            query = query.join(Cliente).join(Operadora).filter(
                or_(
                    Cliente.razao_social.ilike(busca_term),
                    Cliente.nome_sat.ilike(busca_term),
                    Cliente.cnpj.ilike(busca_term),
                    Operadora.nome.ilike(busca_term)
                )
            )

        if status:
            query = query.filter(Processo.status_processo == status)

        if mes_ano:
            query = query.filter(Processo.mes_ano == mes_ano)

        if operadora_id:
            query = query.join(Cliente).filter(Cliente.operadora_id == operadora_id)

        # Ordenação
        query = query.order_by(desc(Processo.data_atualizacao))

        # Paginação
        page = request.args.get('page', 1, type=int)
        per_page = 10

        processos = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        # Criar formulário de filtros
        form = ProcessoFiltroForm(request.args)

        return render_template(
            'processos/index.html',
            processos=processos,
            form=form
        )

    except Exception as e:
        logger.error(f"Erro ao carregar processos: {str(e)}")
        flash('Erro ao carregar processos. Tente novamente.', 'danger')
        return redirect(url_for('home_blueprint.index'))


@bp.route('/novo', methods=['GET', 'POST'])
@verify_user_jwt
def novo():
    """Criar novo processo"""

    form = ProcessoForm()

    if form.validate_on_submit():
        try:
            # Validar formato mês/ano
            if not Processo.validar_formato_mes_ano(form.mes_ano.data):
                flash('Formato de mês/ano inválido. Use MM/AAAA.', 'danger')
                return render_template('processos/form.html', form=form, titulo="Novo Processo")

            # Verificar se já existe processo para este cliente/mês/ano
            processo_existente = db.session.query(Processo).filter(
                and_(
                    Processo.cliente_id == form.cliente_id.data,
                    Processo.mes_ano == form.mes_ano.data
                )
            ).first()

            if processo_existente:
                flash('Já existe um processo para este cliente no mês/ano informado.', 'danger')
                return render_template('processos/form.html', form=form, titulo="Novo Processo")

            # Criar novo processo
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

            logger.info(f"Processo criado: {processo.id} - {processo.cliente.razao_social} - {processo.mes_ano}")
            flash('Processo criado com sucesso!', 'success')

            return redirect(url_for('processos_bp.visualizar', id=processo.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar processo: {str(e)}")
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

    # Buscar execuções ordenadas por data (query separada devido ao lazy="dynamic")
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
            # Validar formato mês/ano
            if not Processo.validar_formato_mes_ano(form.mes_ano.data):
                flash('Formato de mês/ano inválido. Use MM/AAAA.', 'danger')
                return render_template('processos/form.html', form=form, titulo="Editar Processo")

            # Verificar se mudou cliente/mês e se já existe outro processo
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

            # Atualizar dados
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

            logger.info(f"Processo atualizado: {processo.id}")
            flash('Processo atualizado com sucesso!', 'success')

            return redirect(url_for('processos_bp.visualizar', id=processo.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar processo: {str(e)}")
            flash('Erro ao atualizar processo. Tente novamente.', 'danger')

    return render_template('processos/form.html', form=form, titulo="Editar Processo")


@bp.route('/excluir/<id>', methods=['POST'])
@verify_user_jwt
def excluir(id):
    """Excluir processo"""

    try:
        processo = db.session.query(Processo).filter(Processo.id == id).first_or_404()

        # Verificar se pode ser excluído (não está em status final)
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

        logger.info(f"Processo excluído: {id} - {cliente_nome} - {mes_ano}")
        flash('Processo excluído com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir processo {id}: {str(e)}")
        flash('Erro ao excluir processo.', 'danger')

    return redirect(url_for('processos_bp.index'))


@bp.route('/aprovar/<id>', methods=['POST'])
@verify_user_jwt
def aprovar(id):
    """Aprovar processo"""

    form = AprovacaoForm()

    if form.validate_on_submit():
        try:
            processo = db.session.query(Processo).filter(Processo.id == id).first_or_404()

            # Verificar se pode ser aprovado
            if not processo.pode_ser_aprovado:
                flash('Este processo não pode ser aprovado no status atual.', 'warning')
                return redirect(url_for('processos_bp.visualizar', id=id))

            # Aprovar processo (precisa implementar usuario_id real)
            usuario_id = "00000000-0000-0000-0000-000000000000"  # TODO: pegar do JWT/sessão
            processo.aprovar(usuario_id, form.observacoes.data)

            db.session.commit()

            logger.info(f"Processo aprovado: {processo.id}")
            flash('Processo aprovado com sucesso!', 'success')

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao aprovar processo {id}: {str(e)}")
            flash('Erro ao aprovar processo.', 'danger')

    return redirect(url_for('processos_bp.visualizar', id=id))


@bp.route('/rejeitar/<id>', methods=['POST'])
@verify_user_jwt
def rejeitar(id):
    """Rejeitar processo"""

    form = AprovacaoForm()

    if form.validate_on_submit():
        try:
            processo = db.session.query(Processo).filter(Processo.id == id).first_or_404()

            # Verificar se está pendente de aprovação
            if not processo.esta_pendente_aprovacao:
                flash('Este processo não está pendente de aprovação.', 'warning')
                return redirect(url_for('processos_bp.visualizar', id=id))

            # Rejeitar processo
            processo.rejeitar(form.observacoes.data)

            db.session.commit()

            logger.info(f"Processo rejeitado: {processo.id}")
            flash('Processo rejeitado.', 'info')

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao rejeitar processo {id}: {str(e)}")
            flash('Erro ao rejeitar processo.', 'danger')

    return redirect(url_for('processos_bp.visualizar', id=id))


@bp.route('/criar-processos-mensais', methods=['GET', 'POST'])
@verify_user_jwt
def criar_processos_mensais():
    """Criar processos mensais automaticamente para todos os clientes ativos"""

    form = CriarProcessosMensaisForm()

    if form.validate_on_submit():
        try:
            # Validar formato mês/ano
            if not Processo.validar_formato_mes_ano(form.mes_ano.data):
                flash('Formato de mês/ano inválido. Use MM/AAAA.', 'danger')
                return render_template('processos/criar_mensais.html', form=form)

            # Query de clientes
            query_clientes = db.session.query(Cliente)\
                .join(Operadora)\
                .filter(
                    Cliente.status_ativo == True,
                    Operadora.status_ativo == True
                )

            # Filtrar por operadora se especificada
            if form.operadora_id.data:
                query_clientes = query_clientes.filter(Cliente.operadora_id == form.operadora_id.data)

            clientes = query_clientes.all()

            # Contadores
            processos_criados = 0
            processos_ja_existentes = 0

            for cliente in clientes:
                # Verificar se já existe processo para este cliente/mês/ano
                processo_existente = db.session.query(Processo).filter(
                    and_(
                        Processo.cliente_id == cliente.id,
                        Processo.mes_ano == form.mes_ano.data
                    )
                ).first()

                if processo_existente:
                    processos_ja_existentes += 1
                    continue

                # Criar novo processo
                processo = Processo(
                    cliente_id=cliente.id,
                    mes_ano=form.mes_ano.data,
                    status_processo=StatusProcesso.AGUARDANDO_DOWNLOAD.value,
                    criado_automaticamente=True
                )

                db.session.add(processo)
                processos_criados += 1

            db.session.commit()

            logger.info(f"Processos mensais criados: {processos_criados} para {form.mes_ano.data}")

            if processos_criados > 0:
                flash(f'Criados {processos_criados} processos para {form.mes_ano.data}!', 'success')

            if processos_ja_existentes > 0:
                flash(f'{processos_ja_existentes} processos já existiam para este período.', 'info')

            if processos_criados == 0 and processos_ja_existentes == 0:
                flash('Nenhum cliente ativo encontrado.', 'warning')

            return redirect(url_for('processos_bp.index'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar processos mensais: {str(e)}")
            flash('Erro ao criar processos mensais.', 'danger')

    return render_template('processos/criar_mensais.html', form=form)


@bp.route('/enviar-sat/<id>', methods=['POST'])
@verify_user_jwt
def enviar_sat(id):
    """Envia processo para o SAT (mock por enquanto)"""

    try:
        processo = db.session.query(Processo).filter(Processo.id == id).first_or_404()

        # Verificar se pode ser enviado para SAT
        if not processo.pode_enviar_sat:
            return jsonify({
                'success': False,
                'message': 'Este processo não pode ser enviado para o SAT no status atual.'
            }), 400

        # Mock do envio para SAT - em produção aqui será chamado o RPA
        processo.enviar_para_sat()

        db.session.commit()

        logger.info(f"Processo enviado para SAT (mock): {processo.id}")

        return jsonify({
            'success': True,
            'message': 'Fatura enviada para o SAT com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao enviar processo {id} para SAT: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor.'
        }), 500


@bp.route('/api/estatisticas')
@verify_user_jwt
def api_estatisticas():
    """API para estatísticas do dashboard"""

    try:
        # Total de processos
        total_processos = db.session.query(Processo).count()

        # Processos por status
        status_counts = {}
        for status in StatusProcesso:
            count = db.session.query(Processo)\
                .filter(Processo.status_processo == status.value)\
                .count()
            status_counts[status.value] = count

        # Processos pendentes de aprovação
        pendentes_aprovacao = db.session.query(Processo)\
            .filter(Processo.status_processo == StatusProcesso.DOWNLOAD_COMPLETO.value)\
            .count()

        # Processos do mês atual
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
        logger.error(f"Erro ao buscar estatísticas: {str(e)}")
        return jsonify({'error': 'Erro interno'}), 500

@bp.route('/aprovar/<string:id>', methods=['POST'])
@verify_user_jwt
def aprovar(id: str):
    """Aprovar uma fatura"""
    try:
        processo = db.session.query(Processo)\
            .filter(Processo.id == id)\
            .first_or_404()

        if not processo.pode_ser_aprovado:
            return jsonify({
                'success': False,
                'message': 'Processo não pode ser aprovado no status atual.'
            }), 400

        observacoes = request.form.get('observacoes', '').strip()

        # Aqui você pegaria o ID do usuário logado
        # Por enquanto usando um mock
        usuario_id = '123e4567-e89b-12d3-a456-426614174000'  # Mock - deve vir do usuário logado

        processo.aprovar(usuario_id, observacoes)
        db.session.commit()

        logger.info(f"Processo aprovado: {id}")

        return jsonify({
            'success': True,
            'message': 'Fatura aprovada com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao aprovar processo {id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor.'
        }), 500


@bp.route('/rejeitar/<string:id>', methods=['POST'])
@verify_user_jwt
def rejeitar(id: str):
    """Rejeitar uma fatura"""
    try:
        processo = db.session.query(Processo)\
            .filter(Processo.id == id)\
            .first_or_404()

        observacoes = request.form.get('observacoes', '').strip()
        if not observacoes:
            return jsonify({
                'success': False,
                'message': 'Motivo da rejeição é obrigatório.'
            }), 400

        processo.rejeitar(observacoes)
        db.session.commit()

        logger.info(f"Processo rejeitado: {id}")

        return jsonify({
            'success': True,
            'message': 'Fatura rejeitada com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao rejeitar processo {id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor.'
        }), 500


@bp.route('/enviar-sat/<string:id>', methods=['POST'])
@verify_user_jwt
def enviar_sat(id: str):
    """Enviar fatura para o SAT"""
    try:
        processo = db.session.query(Processo)\
            .filter(Processo.id == id)\
            .first_or_404()

        if not processo.pode_enviar_sat:
            return jsonify({
                'success': False,
                'message': 'Processo não pode ser enviado para SAT no status atual.'
            }), 400

        # Aqui seria chamado o RPA do SAT
        # Por enquanto apenas marcamos como enviado
        processo.enviar_para_sat()
        db.session.commit()

        logger.info(f"Processo enviado para SAT: {id}")

        return jsonify({
            'success': True,
            'message': 'Fatura enviada para o SAT com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao enviar processo para SAT {id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor.'
        }), 500