
"""
Rotas para gerenciamento de clientes
"""

import csv
import io
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required
from sqlalchemy import or_, and_
from werkzeug.utils import secure_filename

from apps.clientes import bp
from apps.models import Cliente, Operadora
from apps.clientes.forms import ClienteForm, FiltroClienteForm, ImportarClientesForm
from apps import db


@bp.route('/')
@login_required
def index():
    """Lista todos os clientes com filtros e paginação"""

    # Formulário de filtros
    form_filtro = FiltroClienteForm()

    # Parâmetros de paginação
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)  # 20 clientes por página
    
    # Query base com join na operadora
    query = Cliente.query.join(Operadora)

    # Aplicar filtros se fornecidos
    if request.args.get('razao_social'):
        query = query.filter(
            Cliente.razao_social.ilike(f"%{request.args.get('razao_social')}%")
        )
        form_filtro.razao_social.data = request.args.get('razao_social')

    if request.args.get('cnpj'):
        cnpj_filtro = ''.join(filter(str.isdigit, request.args.get('cnpj')))
        query = query.filter(Cliente.cnpj.like(f"%{cnpj_filtro}%"))
        form_filtro.cnpj.data = request.args.get('cnpj')

    if request.args.get('operadora'):
        query = query.filter(Cliente.operadora_id == request.args.get('operadora'))
        form_filtro.operadora.data = request.args.get('operadora')

    if request.args.get('servico'):
        query = query.filter(
            Cliente.servico.ilike(f"%{request.args.get('servico')}%")
        )
        form_filtro.servico.data = request.args.get('servico')

    if request.args.get('unidade'):
        query = query.filter(
            Cliente.unidade.ilike(f"%{request.args.get('unidade')}%")
        )
        form_filtro.unidade.data = request.args.get('unidade')

    if request.args.get('status'):
        if request.args.get('status') == 'ativo':
            query = query.filter(Cliente.status_ativo == True)
        elif request.args.get('status') == 'inativo':
            query = query.filter(Cliente.status_ativo == False)
        form_filtro.status.data = request.args.get('status')

    # Ordenação
    query = query.order_by(Cliente.razao_social)

    # Paginação
    pagination = query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    clientes = pagination.items

    # Estatísticas para cards (consultas separadas para performance)
    total_clientes = Cliente.query.count()
    clientes_ativos = Cliente.query.filter_by(status_ativo=True).count()
    clientes_com_rpa = Cliente.query.join(Operadora).filter(
        and_(Cliente.status_ativo == True, Operadora.possui_rpa == True)
    ).count()
    clientes_sem_rpa = Cliente.query.join(Operadora).filter(
        and_(Cliente.status_ativo == True, Operadora.possui_rpa == False)
    ).count()

    return render_template(
        'clientes/index.html',
        clientes=clientes,
        pagination=pagination,
        form_filtro=form_filtro,
        total_clientes=total_clientes,
        clientes_ativos=clientes_ativos,
        clientes_com_rpa=clientes_com_rpa,
        clientes_sem_rpa=clientes_sem_rpa
    )


@bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    """Cadastra novo cliente"""

    form = ClienteForm()

    if form.validate_on_submit():
        try:
            # Cria novo cliente
            cliente = Cliente(
                razao_social=form.razao_social.data.strip(),
                nome_sat=form.nome_sat.data.strip(),
                cnpj=form.cnpj.data.strip(),
                operadora_id=form.operadora_id.data,
                servico=form.servico.data.strip(),
                unidade=form.unidade.data.strip(),
                filtro=form.filtro.data.strip() if form.filtro.data else None,
                dados_sat=form.dados_sat.data.strip() if form.dados_sat.data else None,
                site_emissao=form.site_emissao.data.strip() if form.site_emissao.data else None,
                login_portal=form.login_portal.data.strip() if form.login_portal.data else None,
                senha_portal=form.senha_portal.data.strip() if form.senha_portal.data else None,
                cpf=form.cpf.data.strip() if form.cpf.data else None,
                status_ativo=form.status_ativo.data
            )

            # Gera hash único
            cliente.atualizar_hash()

            db.session.add(cliente)
            db.session.commit()

            flash(f'Cliente "{cliente.razao_social}" cadastrado com sucesso!', 'success')
            return redirect(url_for('clientes_bp.visualizar', cliente_id=cliente.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar cliente: {str(e)}', 'error')
            print(f"Erro ao cadastrar novo cliente: {str(e)}")

    return render_template('clientes/form.html', form=form, title='Novo Cliente')


@bp.route('/editar/<uuid:cliente_id>', methods=['GET', 'POST'])
@login_required
def editar(cliente_id):
    """Edita cliente existente"""

    cliente = Cliente.query.get_or_404(cliente_id)
    form = ClienteForm(obj=cliente)
    form._obj = cliente  # Para validação de duplicatas

    if form.validate_on_submit():
        try:
            # Atualiza dados
            cliente.razao_social = form.razao_social.data.strip()
            cliente.nome_sat = form.nome_sat.data.strip()
            cliente.cnpj = form.cnpj.data.strip()
            cliente.operadora_id = form.operadora_id.data
            cliente.servico = form.servico.data.strip()
            cliente.unidade = form.unidade.data.strip()
            cliente.filtro = form.filtro.data.strip() if form.filtro.data else None
            cliente.dados_sat = form.dados_sat.data.strip() if form.dados_sat.data else None
            cliente.site_emissao = form.site_emissao.data.strip() if form.site_emissao.data else None
            cliente.login_portal = form.login_portal.data.strip() if form.login_portal.data else None
            cliente.senha_portal = form.senha_portal.data.strip() if form.senha_portal.data else None
            cliente.cpf = form.cpf.data.strip() if form.cpf.data else None
            cliente.status_ativo = form.status_ativo.data

            # Atualiza hash único
            cliente.atualizar_hash()

            db.session.commit()

            flash(f'Cliente "{cliente.razao_social}" atualizado com sucesso!', 'success')
            return redirect(url_for('clientes_bp.visualizar', cliente_id=cliente.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar cliente: {str(e)}', 'error')
            print(f"Erro ao atualizar cliente {cliente_id}: {str(e)}")

    return render_template(
        'clientes/form.html', 
        form=form, 
        cliente=cliente,
        title=f'Editar Cliente - {cliente.razao_social}'
    )


@bp.route('/visualizar/<uuid:cliente_id>')
@login_required
def visualizar(cliente_id):
    """Visualiza detalhes do cliente"""

    cliente = Cliente.query.get_or_404(cliente_id)

    # Busca estatísticas de processos (quando implementados)
    # total_processos = cliente.processos.count()
    # processos_ativos = cliente.processos.filter_by(status_ativo=True).count()

    return render_template(
        'clientes/detalhes.html',
        cliente=cliente,
        # total_processos=total_processos,
        # processos_ativos=processos_ativos
    )


@bp.route('/excluir/<uuid:cliente_id>', methods=['POST'])
@login_required
def excluir(cliente_id):
    """Exclui cliente (se não tiver processos vinculados)"""

    cliente = Cliente.query.get_or_404(cliente_id)

    try:
        # Verifica se tem processos vinculados (quando implementados)
        # if cliente.processos.count() > 0:
        #     flash(
        #         f'Não é possível excluir o cliente "{cliente.razao_social}" pois existem '
        #         f'{cliente.processos.count()} processo(s) vinculado(s).', 
        #         'warning'
        #     )
        #     return redirect(url_for('clientes_bp.index'))

        razao_social = cliente.razao_social
        db.session.delete(cliente)
        db.session.commit()

        flash(f'Cliente "{razao_social}" excluído com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir cliente: {str(e)}', 'error')

    return redirect(url_for('clientes_bp.index'))


@bp.route('/toggle-status/<uuid:cliente_id>', methods=['POST'])
@login_required
def toggle_status(cliente_id):
    """Alterna status ativo/inativo do cliente"""

    cliente = Cliente.query.get_or_404(cliente_id)

    try:
        cliente.status_ativo = not cliente.status_ativo
        db.session.commit()

        status_texto = 'ativado' if cliente.status_ativo else 'desativado'
        flash(f'Cliente "{cliente.razao_social}" {status_texto} com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao alterar status do cliente: {str(e)}', 'error')

    return redirect(url_for('clientes_bp.index'))


@bp.route('/importar', methods=['GET', 'POST'])
@login_required
def importar():
    """Importa clientes via CSV"""

    form = ImportarClientesForm()

    if form.validate_on_submit():
        try:
            arquivo = form.arquivo_csv.data
            sobrescrever = form.sobrescrever_existentes.data
            
            # Lê o arquivo CSV
            stream = io.StringIO(arquivo.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.DictReader(stream)
            
            clientes_processados = 0
            clientes_criados = 0
            clientes_atualizados = 0
            erros = []

            # Mapeia operadoras por nome para busca rápida (normalizado)
            operadoras_map = {}
            for op in Operadora.query.all():
                # Normaliza nome removendo espaços, acentos, hífens
                nome_normalizado = op.nome.upper().replace(' ', '').replace('-', '').replace('_', '')
                operadoras_map[nome_normalizado] = op
                # Também mapeia nome original
                operadoras_map[op.nome.upper()] = op

            for row_num, row in enumerate(csv_input, start=2):  # Start=2 por causa do header
                try:
                    # Validações básicas
                    if not row.get('CNPJ') or not row.get('OPERADORA'):
                        erros.append(f"Linha {row_num}: CNPJ e OPERADORA são obrigatórios")
                        continue

                    # Busca operadora com normalização flexível
                    operadora_csv = row.get('OPERADORA', '').strip().upper()
                    operadora_normalizada = operadora_csv.replace(' ', '').replace('-', '').replace('_', '')
                    
                    # Tenta buscar com nome normalizado e depois com nome original
                    operadora = operadoras_map.get(operadora_normalizada) or operadoras_map.get(operadora_csv)
                    
                    if not operadora:
                        erros.append(f"Linha {row_num}: Operadora '{operadora_csv}' não encontrada. Operadoras disponíveis: {', '.join(set([o.nome for o in Operadora.query.all()]))}")
                        continue

                    # Limpa dados
                    cnpj = ''.join(filter(str.isdigit, row.get('CNPJ', '')))
                    razao_social = row.get('RAZÃO SOCIAL', '').strip()
                    nome_sat = row.get('NOME SAT', '').strip()
                    servico = row.get('SERVIÇO', '').strip()
                    unidade = row.get('UNIDADE / FILTRO SAT', '').strip()

                    if not all([cnpj, razao_social, nome_sat, servico, unidade]):
                        erros.append(f"Linha {row_num}: Campos obrigatórios em falta")
                        continue

                    # Verifica se cliente já existe
                    cliente_existente = Cliente.query.filter_by(
                        cnpj=cnpj,
                        operadora_id=operadora.id,
                        unidade=unidade,
                        servico=servico
                    ).first()

                    if cliente_existente and not sobrescrever:
                        erros.append(f"Linha {row_num}: Cliente já existe (CNPJ: {cnpj})")
                        continue

                    # Cria ou atualiza cliente
                    if cliente_existente:
                        cliente = cliente_existente
                        clientes_atualizados += 1
                    else:
                        cliente = Cliente()
                        clientes_criados += 1

                    # Preenche dados
                    cliente.razao_social = razao_social
                    cliente.nome_sat = nome_sat
                    cliente.cnpj = cnpj
                    cliente.operadora_id = operadora.id
                    cliente.servico = servico
                    cliente.unidade = unidade
                    cliente.filtro = row.get('FILTRO', '').strip() or None
                    cliente.dados_sat = row.get('DADOS SAT', '').strip() or None
                    cliente.site_emissao = row.get('SITE PARA EMISSÃO', '').strip() or None
                    cliente.login_portal = row.get('LOGIN', '').strip() or None
                    cliente.senha_portal = row.get('SENHA', '').strip() or None
                    cliente.cpf = row.get('CPF', '').strip() or None
                    cliente.status_ativo = row.get('STATUS', '1') != '0'

                    # Atualiza hash
                    cliente.atualizar_hash()

                    if not cliente_existente:
                        db.session.add(cliente)

                    clientes_processados += 1

                except Exception as e:
                    erros.append(f"Linha {row_num}: Erro ao processar - {str(e)}")

            # Salva no banco
            db.session.commit()

            # Mensagem de resultado
            mensagem = f"Importação concluída! {clientes_processados} clientes processados. "
            mensagem += f"Criados: {clientes_criados}, Atualizados: {clientes_atualizados}"
            
            if erros:
                mensagem += f", Erros: {len(erros)}"
                
            flash(mensagem, 'success' if not erros else 'warning')
            
            if erros:
                # Mostra primeiros 10 erros
                for erro in erros[:10]:
                    flash(erro, 'error')
                if len(erros) > 10:
                    flash(f"... e mais {len(erros) - 10} erros", 'error')

            return redirect(url_for('clientes_bp.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao processar arquivo: {str(e)}', 'error')

    return render_template('clientes/importar.html', form=form)


@bp.route('/api/clientes-ativos')
@login_required
def api_clientes_ativos():
    """API para buscar clientes ativos (para usar em selects)"""

    clientes = Cliente.query.filter_by(status_ativo=True).order_by(Cliente.razao_social).all()

    return jsonify([
        {
            'id': str(cliente.id),
            'razao_social': cliente.razao_social,
            'cnpj': cliente.cnpj,
            'operadora': cliente.operadora.nome if cliente.operadora else None,
            'hash_unico': cliente.hash_unico
        }
        for cliente in clientes
    ])
