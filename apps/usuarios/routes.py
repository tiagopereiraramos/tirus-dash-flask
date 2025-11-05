"""
Rotas para gerenciamento de usuários
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from apps.authentication.util import hash_pass
from sqlalchemy import or_

from apps import db
from apps.authentication.models import Users
import logging

logger = logging.getLogger(__name__)
usuarios_bp = Blueprint('usuarios_bp', __name__)


def verificar_permissao_admin():
    """Verifica se o usuário atual pode gerenciar usuários"""
    if not current_user.is_authenticated:
        return False
    return getattr(current_user, 'is_admin', False)


@usuarios_bp.route('/')
@login_required
def index():
    """Lista todos os usuários com paginação"""

    # Verificar permissão
    if not verificar_permissao_admin():
        flash('Acesso negado. Apenas administradores podem gerenciar usuários.', 'error')
        return redirect(url_for('home_bp.index'))

    # Parâmetros de paginação
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Query base
    query = Users.query

    # Aplicar filtros se fornecidos
    if request.args.get('username'):
        query = query.filter(Users.username.ilike(f"%{request.args.get('username')}%"))

    if request.args.get('email'):
        query = query.filter(Users.email.ilike(f"%{request.args.get('email')}%"))

    # Ordenação
    query = query.order_by(Users.username)

    # Paginação
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    return render_template('usuarios/index.html',
                           usuarios=pagination.items,
                           pagination=pagination)


@usuarios_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    """Criar novo usuário"""

    # Verificar permissão
    if not verificar_permissao_admin():
        flash('Acesso negado. Apenas administradores podem criar usuários.', 'error')
        return redirect(url_for('usuarios.index'))

    form = UsuarioForm()

    if form.validate_on_submit():
        try:
            # Verificar se senha foi fornecida para novo usuário
            if not form.password.data:
                flash('Senha é obrigatória para novos usuários.', 'error')
                return render_template('usuarios/form.html', form=form, acao='Criar')

            # Criar novo usuário
            usuario = Usuario(
                nome_completo=form.nome_completo.data,
                email=form.email.data,
                username=form.username.data,
                telefone=form.telefone.data,
                perfil_usuario=form.perfil_usuario.data,
                status_ativo=form.status_ativo.data,
                password_hash=generate_password_hash(form.password.data)
            )

            db.session.add(usuario)
            db.session.commit()

            logger.info(
                f"Usuário criado: {usuario.username} por {current_user.username}")
            flash(
                f'Usuário {usuario.nome_completo} criado com sucesso!', 'success')
            return redirect(url_for('usuarios.index'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar usuário: {str(e)}")
            flash('Erro ao criar usuário. Tente novamente.', 'error')

    return render_template('usuarios/form.html', form=form, acao='Criar')


@usuarios_bp.route('/editar/<id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    """Editar usuário existente"""

    # Verificar permissão
    if not verificar_permissao_admin():
        flash('Acesso negado. Apenas administradores podem editar usuários.', 'error')
        return redirect(url_for('usuarios.index'))

    usuario = Usuario.query.get_or_404(id)
    form = UsuarioForm(usuario_id=usuario.id)

    if form.validate_on_submit():
        try:
            # Atualizar dados
            usuario.nome_completo = form.nome_completo.data
            usuario.email = form.email.data
            usuario.username = form.username.data
            usuario.telefone = form.telefone.data
            usuario.perfil_usuario = form.perfil_usuario.data
            usuario.status_ativo = form.status_ativo.data

            # Atualizar senha se fornecida
            if form.password.data:
                usuario.password_hash = generate_password_hash(
                    form.password.data)

            db.session.commit()

            logger.info(
                f"Usuário editado: {usuario.username} por {current_user.username}")
            flash(
                f'Usuário {usuario.nome_completo} atualizado com sucesso!', 'success')
            return redirect(url_for('usuarios.index'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar usuário {id}: {str(e)}")
            flash('Erro ao atualizar usuário. Tente novamente.', 'error')

    # Preencher formulário com dados existentes
    if request.method == 'GET':
        form.nome_completo.data = usuario.nome_completo
        form.email.data = usuario.email
        form.username.data = usuario.username
        form.telefone.data = usuario.telefone
        form.perfil_usuario.data = usuario.perfil_usuario
        form.status_ativo.data = usuario.status_ativo

    return render_template('usuarios/form.html', form=form, acao='Editar', usuario=usuario)


@usuarios_bp.route('/detalhes/<id>')
@login_required
def detalhes(id):
    """Visualizar detalhes do usuário"""

    # Verificar permissão (administradores podem ver todos, usuários apenas próprio perfil)
    if not verificar_permissao_admin() and str(current_user.id) != str(id):
        flash('Acesso negado.', 'error')
        return redirect(url_for('home.index'))

    usuario = Usuario.query.get_or_404(id)

    # Estatísticas do usuário
    total_processos_aprovados = usuario.processos_aprovados.count()
    total_execucoes = usuario.execucoes_realizadas.count()

    return render_template('usuarios/detalhes.html',
                           usuario=usuario,
                           total_processos_aprovados=total_processos_aprovados,
                           total_execucoes=total_execucoes)


@usuarios_bp.route('/ativar/<id>', methods=['POST'])
@login_required
def ativar(id):
    """Ativar usuário"""

    logger.info(
        f"Tentativa de ativar usuário {id} por {current_user.username}")

    # Verificar permissão
    if not verificar_permissao_admin():
        logger.warning(
            f"Acesso negado para ativar usuário - usuário {current_user.username} não é admin")
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403

    try:
        usuario = Usuario.query.get_or_404(id)
        logger.info(f"Usuário encontrado: {usuario.username}")
        usuario.ativar()
        db.session.commit()

        logger.info(
            f"Usuário ativado: {usuario.username} por {current_user.username}")
        return jsonify({
            'success': True,
            'message': f'Usuário {usuario.nome_completo} ativado com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao ativar usuário {id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao ativar usuário'}), 500


@usuarios_bp.route('/desativar/<id>', methods=['POST'])
@login_required
def desativar(id):
    """Desativar usuário"""

    logger.info(
        f"Tentativa de desativar usuário {id} por {current_user.username}")

    # Verificar permissão
    if not verificar_permissao_admin():
        logger.warning(
            f"Acesso negado para desativar usuário - usuário {current_user.username} não é admin")
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403

    # Não permitir desativar próprio usuário
    if str(current_user.id) == str(id):
        logger.warning(
            f"Tentativa de desativar próprio usuário por {current_user.username}")
        return jsonify({'success': False, 'message': 'Não é possível desativar seu próprio usuário'}), 400

    try:
        usuario = Usuario.query.get_or_404(id)
        logger.info(f"Usuário encontrado: {usuario.username}")
        usuario.desativar()
        db.session.commit()

        logger.info(
            f"Usuário desativado: {usuario.username} por {current_user.username}")
        return jsonify({
            'success': True,
            'message': f'Usuário {usuario.nome_completo} desativado com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao desativar usuário {id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao desativar usuário'}), 500


@usuarios_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    """Editar perfil do usuário logado"""

    form = PerfilUsuarioForm(usuario_atual=current_user)

    if form.validate_on_submit():
        try:
            current_user.nome_completo = form.nome_completo.data
            current_user.email = form.email.data
            current_user.telefone = form.telefone.data

            db.session.commit()

            logger.info(f"Perfil atualizado: {current_user.username}")
            flash('Perfil atualizado com sucesso!', 'success')
            return redirect(url_for('usuarios.perfil'))

        except Exception as e:
            db.session.rollback()
            logger.error(
                f"Erro ao atualizar perfil do usuário {current_user.id}: {str(e)}")
            flash('Erro ao atualizar perfil. Tente novamente.', 'error')

    # Preencher formulário com dados atuais
    if request.method == 'GET':
        form.nome_completo.data = current_user.nome_completo
        form.email.data = current_user.email
        form.telefone.data = current_user.telefone

    return render_template('usuarios/perfil.html', form=form)


@usuarios_bp.route('/alterar-senha', methods=['GET', 'POST'])
@login_required
def alterar_senha():
    """Alterar senha do usuário logado"""

    form = AlterarSenhaForm()

    if form.validate_on_submit():
        try:
            # Verificar senha atual
            if not current_user.check_password(form.senha_atual.data):
                flash('Senha atual incorreta.', 'error')
                return render_template('usuarios/alterar_senha.html', form=form)

            # Atualizar senha
            current_user.set_password(form.nova_senha.data)
            db.session.commit()

            logger.info(f"Senha alterada: {current_user.username}")
            flash('Senha alterada com sucesso!', 'success')
            return redirect(url_for('usuarios.perfil'))

        except Exception as e:
            db.session.rollback()
            logger.error(
                f"Erro ao alterar senha do usuário {current_user.id}: {str(e)}")
            flash('Erro ao alterar senha. Tente novamente.', 'error')

    return render_template('usuarios/alterar_senha.html', form=form)
