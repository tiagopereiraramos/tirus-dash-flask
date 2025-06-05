
"""
Rotas para gerenciamento de operadoras
"""

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from sqlalchemy import or_

from apps.operadoras import bp
from apps.models import Operadora
from apps.operadoras.forms import OperadoraForm, FiltroOperadoraForm
from apps import db


@bp.route('/')
@login_required
def index():
    """Lista todas as operadoras com filtros"""
    
    # Formulário de filtros
    form_filtro = FiltroOperadoraForm()
    
    # Query base
    query = Operadora.query
    
    # Aplicar filtros se fornecidos
    if request.args.get('nome'):
        query = query.filter(
            Operadora.nome.ilike(f"%{request.args.get('nome')}%")
        )
        form_filtro.nome.data = request.args.get('nome')
    
    if request.args.get('codigo'):
        query = query.filter(
            Operadora.codigo.ilike(f"%{request.args.get('codigo')}%")
        )
        form_filtro.codigo.data = request.args.get('codigo')
    
    if request.args.get('status'):
        if request.args.get('status') == 'ativo':
            query = query.filter(Operadora.status_ativo == True)
        elif request.args.get('status') == 'inativo':
            query = query.filter(Operadora.status_ativo == False)
        form_filtro.status.data = request.args.get('status')
    
    if request.args.get('rpa'):
        if request.args.get('rpa') == 'com_rpa':
            query = query.filter(Operadora.possui_rpa == True)
        elif request.args.get('rpa') == 'sem_rpa':
            query = query.filter(Operadora.possui_rpa == False)
        form_filtro.rpa.data = request.args.get('rpa')
    
    # Ordenação
    query = query.order_by(Operadora.nome)
    
    # Paginação
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    operadoras = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Estatísticas para cards
    total_operadoras = Operadora.query.count()
    operadoras_ativas = Operadora.query.filter_by(status_ativo=True).count()
    operadoras_com_rpa = Operadora.query.filter_by(possui_rpa=True).count()
    operadoras_sem_rpa = Operadora.query.filter_by(possui_rpa=False).count()
    
    return render_template(
        'operadoras/index.html',
        operadoras=operadoras,
        form_filtro=form_filtro,
        total_operadoras=total_operadoras,
        operadoras_ativas=operadoras_ativas,
        operadoras_com_rpa=operadoras_com_rpa,
        operadoras_sem_rpa=operadoras_sem_rpa
    )


@bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova():
    """Cadastra nova operadora"""
    
    form = OperadoraForm()
    
    if form.validate_on_submit():
        try:
            # Cria nova operadora
            operadora = Operadora(
                nome=form.nome.data,
                codigo=form.codigo.data.upper(),
                possui_rpa=form.possui_rpa.data,
                status_ativo=form.status_ativo.data,
                url_portal=form.url_portal.data or None,
                instrucoes_acesso=form.instrucoes_acesso.data or None,
                classe_rpa=form.classe_rpa.data or None
            )
            
            db.session.add(operadora)
            db.session.commit()
            
            flash(f'Operadora "{operadora.nome}" cadastrada com sucesso!', 'success')
            return redirect(url_for('operadoras_bp.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar operadora: {str(e)}', 'error')
    
    return render_template('operadoras/form.html', form=form, title='Nova Operadora')


@bp.route('/editar/<uuid:operadora_id>', methods=['GET', 'POST'])
@login_required
def editar(operadora_id):
    """Edita operadora existente"""
    
    operadora = Operadora.query.get_or_404(operadora_id)
    form = OperadoraForm(obj=operadora)
    form._obj = operadora  # Para validação de duplicatas
    
    if form.validate_on_submit():
        try:
            # Atualiza dados
            operadora.nome = form.nome.data
            operadora.codigo = form.codigo.data.upper()
            operadora.possui_rpa = form.possui_rpa.data
            operadora.status_ativo = form.status_ativo.data
            operadora.url_portal = form.url_portal.data or None
            operadora.instrucoes_acesso = form.instrucoes_acesso.data or None
            operadora.classe_rpa = form.classe_rpa.data or None
            
            db.session.commit()
            
            flash(f'Operadora "{operadora.nome}" atualizada com sucesso!', 'success')
            return redirect(url_for('operadoras_bp.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar operadora: {str(e)}', 'error')
    
    return render_template(
        'operadoras/form.html', 
        form=form, 
        operadora=operadora,
        title=f'Editar Operadora - {operadora.nome}'
    )


@bp.route('/visualizar/<uuid:operadora_id>')
@login_required
def visualizar(operadora_id):
    """Visualiza detalhes da operadora"""
    
    operadora = Operadora.query.get_or_404(operadora_id)
    
    # Busca estatísticas de clientes
    total_clientes = operadora.clientes.count()
    clientes_ativos = operadora.clientes.filter_by(status_ativo=True).count()
    
    return render_template(
        'operadoras/detalhes.html',
        operadora=operadora,
        total_clientes=total_clientes,
        clientes_ativos=clientes_ativos
    )


@bp.route('/excluir/<uuid:operadora_id>', methods=['POST'])
@login_required
def excluir(operadora_id):
    """Exclui operadora (se não tiver clientes vinculados)"""
    
    operadora = Operadora.query.get_or_404(operadora_id)
    
    try:
        # Verifica se tem clientes vinculados
        if operadora.clientes.count() > 0:
            flash(
                f'Não é possível excluir a operadora "{operadora.nome}" pois existem '
                f'{operadora.clientes.count()} cliente(s) vinculado(s).', 
                'warning'
            )
            return redirect(url_for('operadoras_bp.index'))
        
        nome_operadora = operadora.nome
        db.session.delete(operadora)
        db.session.commit()
        
        flash(f'Operadora "{nome_operadora}" excluída com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir operadora: {str(e)}', 'error')
    
    return redirect(url_for('operadoras_bp.index'))


@bp.route('/toggle-status/<uuid:operadora_id>', methods=['POST'])
@login_required
def toggle_status(operadora_id):
    """Alterna status ativo/inativo da operadora"""
    
    operadora = Operadora.query.get_or_404(operadora_id)
    
    try:
        operadora.status_ativo = not operadora.status_ativo
        db.session.commit()
        
        status_texto = 'ativada' if operadora.status_ativo else 'desativada'
        flash(f'Operadora "{operadora.nome}" {status_texto} com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao alterar status da operadora: {str(e)}', 'error')
    
    return redirect(url_for('operadoras_bp.index'))


@bp.route('/api/operadoras-ativas')
@login_required
def api_operadoras_ativas():
    """API para buscar operadoras ativas (para usar em selects)"""
    
    operadoras = Operadora.query.filter_by(status_ativo=True).order_by(Operadora.nome).all()
    
    return jsonify([
        {
            'id': str(operadora.id),
            'nome': operadora.nome,
            'codigo': operadora.codigo,
            'possui_rpa': operadora.possui_rpa
        }
        for operadora in operadoras
    ])
