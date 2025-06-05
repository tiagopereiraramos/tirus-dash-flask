# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os
import hashlib
import binascii
from functools import wraps
from flask import redirect, url_for, session, flash
from flask_login import current_user

# Inspiration -> https://www.vitoshacademy.com/hashing-passwords-in-python/


def hash_pass(password):
    """Hash a password for storing."""

    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'),
                                  salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash)  # return bytes


def verify_pass(provided_password, stored_password):
    """Verify a stored password against one provided by user"""

    stored_password = stored_password.decode('ascii')
    salt = stored_password[:64]
    stored_password = stored_password[64:]
    pwdhash = hashlib.pbkdf2_hmac('sha512',
                                  provided_password.encode('utf-8'),
                                  salt.encode('ascii'),
                                  100000)
    pwdhash = binascii.hexlify(pwdhash).decode('ascii')
    return pwdhash == stored_password


def verify_user_jwt(f):
    """
    Decorator para verificar se o usuário está autenticado
    Redireciona para login se não estiver autenticado
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verifica se o usuário está autenticado via Flask-Login
        if not current_user.is_authenticated:
            flash('Você precisa estar logado para acessar esta página.', 'warning')
            return redirect(url_for('authentication_blueprint.login'))
        
        # Verifica se o usuário está ativo (usando o campo correto do modelo Users)
        if hasattr(current_user, 'active') and not current_user.active:
            flash('Sua conta está inativa. Entre em contato com o administrador.', 'danger')
            return redirect(url_for('authentication_blueprint.login'))
        
        return f(*args, **kwargs)
    
    return decorated_function
