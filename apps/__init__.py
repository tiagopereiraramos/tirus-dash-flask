# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from importlib import import_module


db = SQLAlchemy()
login_manager = LoginManager()


def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)


def register_blueprints(app):
    for module_name in ('authentication', 'home'):
        module = import_module('apps.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)


def configure_database(app):

    with app.app_context():
        try:
            db.create_all()
        except Exception as e:

            print('> Error: DBMS Exception: ' + str(e) )

            # fallback to SQLite
            basedir = os.path.abspath(os.path.dirname(__file__))
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db.sqlite3')

            print('> Fallback to SQLite ')
            db.create_all()

    @app.teardown_request
    def shutdown_session(exception=None):
        db.session.remove()

from apps.authentication.oauth import github_blueprint

def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)
    register_extensions(app)
    register_blueprints(app)
    app.register_blueprint(github_blueprint, url_prefix="/login")    
    configure_database(app)

    # Blueprint de Home adicional
    from apps.home.routes import home_bp
    app.register_blueprint(home_bp)

    # Blueprints específicos dos módulos
    from apps.operadoras import bp as operadoras_bp
    from apps.clientes import bp as clientes_bp  
    from apps.processos import bp as processos_bp

    app.register_blueprint(operadoras_bp, url_prefix='/operadoras')
    app.register_blueprint(clientes_bp, url_prefix='/clientes')
    app.register_blueprint(processos_bp, url_prefix='/processos')

    # Adicionar função csrf_token ao contexto global do Jinja2
    @app.template_global()
    def csrf_token():
        try:
            from flask_wtf.csrf import generate_csrf
            return generate_csrf()
        except Exception:
            return ""

    # Context processor para injetar variável segment em todos os templates
    @app.context_processor
    def inject_segment():
        from flask import request
        try:
            # Extrai o primeiro segmento após a raiz (ex: /operadoras/123 -> 'operadoras')
            segment = request.path.split('/')[1] if len(request.path.split('/')) > 1 else 'index'
            if not segment:
                segment = 'index'
            return dict(segment=segment)
        except Exception:
            return dict(segment='index')

    # Rota raiz que redireciona para o dashboard
    @app.route('/')
    def root():
        from flask import redirect, url_for
        return redirect(url_for('home_bp.index'))
    return app