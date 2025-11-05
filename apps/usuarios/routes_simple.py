# -*- encoding: utf-8 -*-
"""
Rotas SIMPLIFICADAS para gerenciamento de usuários (CRUD para modelo Users)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from apps.authentication.util import hash_pass

from apps import db
from apps.authentication.models import Users
import logging
import requests

logger = logging.getLogger(__name__)
usuarios_bp = Blueprint('usuarios_bp', __name__)


def verificar_permissao_admin():
    """Verifica se o usuário atual é admin"""
    return current_user.is_authenticated and getattr(current_user, 'is_admin', False)


@usuarios_bp.route('/')
@login_required
def index():
    """Lista todos os usuários"""
    if not verificar_permissao_admin():
        flash('Acesso negado. Apenas administradores podem gerenciar usuários.', 'error')
        return redirect(url_for('home.index'))

    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Query
    query = Users.query.order_by(Users.username)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('usuarios/index.html',
                           usuarios=pagination.items,
                           pagination=pagination)


@usuarios_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    """Criar novo usuário"""
    if not verificar_permissao_admin():
        flash('Acesso negado.', 'error')
        return redirect(url_for('usuarios_bp.index'))

    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            is_admin = request.form.get('is_admin') == 'on'
            api_externa_token = request.form.get('api_externa_token', '')

            # Validações básicas
            if not username or not email or not password:
                flash('Preencha todos os campos obrigatórios.', 'error')
                return render_template('usuarios/form_simple.html', usuario=None)

            # Verificar se username ou email já existem
            if Users.query.filter_by(username=username).first():
                flash('Nome de usuário já existe.', 'error')
                return render_template('usuarios/form_simple.html', usuario=None)

            if Users.query.filter_by(email=email).first():
                flash('Email já está em uso.', 'error')
                return render_template('usuarios/form_simple.html', usuario=None)

            # Criar usuário
            user = Users(
                username=username,
                email=email,
                password=hash_pass(password),
                is_admin=is_admin,
                api_externa_token=api_externa_token if api_externa_token else None
            )

            db.session.add(user)
            db.session.commit()

            logger.info(f"Usuário criado: {username} por {current_user.username}")
            flash(f'Usuário {username} criado com sucesso!', 'success')
            return redirect(url_for('usuarios_bp.index'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar usuário: {str(e)}")
            flash('Erro ao criar usuário. Tente novamente.', 'error')

    return render_template('usuarios/form_simple.html', usuario=None)


@usuarios_bp.route('/editar/<int:user_id>', methods=['GET', 'POST'])
@login_required
def editar(user_id):
    """Editar usuário existente"""
    if not verificar_permissao_admin():
        flash('Acesso negado.', 'error')
        return redirect(url_for('usuarios_bp.index'))

    usuario = Users.query.get_or_404(user_id)

    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            is_admin = request.form.get('is_admin') == 'on'
            api_externa_token = request.form.get('api_externa_token', '')

            # Verificar duplicações (exceto próprio usuário)
            existing_user = Users.query.filter_by(username=username).first()
            if existing_user and existing_user.id != user_id:
                flash('Nome de usuário já existe.', 'error')
                return render_template('usuarios/form_simple.html', usuario=usuario)

            existing_email = Users.query.filter_by(email=email).first()
            if existing_email and existing_email.id != user_id:
                flash('Email já está em uso.', 'error')
                return render_template('usuarios/form_simple.html', usuario=usuario)

            # Atualizar
            usuario.username = username
            usuario.email = email
            usuario.is_admin = is_admin
            usuario.api_externa_token = api_externa_token if api_externa_token else None

            # Atualizar senha apenas se fornecida
            if password:
                usuario.password = hash_pass(password)

            db.session.commit()

            logger.info(f"Usuário editado: {username} por {current_user.username}")
            flash(f'Usuário {username} atualizado com sucesso!', 'success')
            return redirect(url_for('usuarios_bp.index'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar usuário {user_id}: {str(e)}")
            flash('Erro ao atualizar usuário. Tente novamente.', 'error')

    return render_template('usuarios/form_simple.html', usuario=usuario)


@usuarios_bp.route('/excluir/<int:user_id>', methods=['POST'])
@login_required
def excluir(user_id):
    """Excluir usuário"""
    if not verificar_permissao_admin():
        flash('Acesso negado.', 'error')
        return redirect(url_for('usuarios_bp.index'))

    # Não permitir excluir próprio usuário
    if current_user.id == user_id:
        flash('Não é possível excluir seu próprio usuário.', 'error')
        return redirect(url_for('usuarios_bp.index'))

    try:
        usuario = Users.query.get_or_404(user_id)
        username = usuario.username

        db.session.delete(usuario)
        db.session.commit()

        logger.info(f"Usuário excluído: {username} por {current_user.username}")
        flash(f'Usuário {username} excluído com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir usuário {user_id}: {str(e)}")
        flash('Erro ao excluir usuário. Tente novamente.', 'error')

    return redirect(url_for('usuarios_bp.index'))


@usuarios_bp.route('/testar-jwt', methods=['POST'])
@login_required
def testar_jwt():
    """Testa se um JWT é válido na API externa"""
    if not verificar_permissao_admin():
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    try:
        data = request.get_json()
        token = data.get('token', '').strip()
        
        if not token:
            return jsonify({'success': False, 'error': 'Token não fornecido'}), 400
        
        # Testar o token na API externa
        api_url = 'http://191.252.218.230:8000/health'
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': 'Token JWT válido! Conectado à API externa com sucesso.',
                'api_status': response.json()
            })
        elif response.status_code == 401:
            return jsonify({
                'success': False,
                'error': 'Token inválido ou expirado. Verifique se o token está correto.'
            }), 401
        else:
            return jsonify({
                'success': False,
                'error': f'Erro na API externa (HTTP {response.status_code})'
            }), 500
            
    except requests.Timeout:
        return jsonify({
            'success': False,
            'error': 'Timeout ao conectar com a API externa. Tente novamente.'
        }), 504
    except requests.ConnectionError:
        return jsonify({
            'success': False,
            'error': 'Não foi possível conectar à API externa. Verifique a conexão.'
        }), 503
    except Exception as e:
        logger.error(f"Erro ao testar JWT: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erro ao testar token: {str(e)}'
        }), 500
