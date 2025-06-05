# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps.home import blueprint
from flask import render_template, request, Blueprint
from flask_login import login_required
from jinja2 import TemplateNotFound

# Blueprint específico para home
home_bp = Blueprint('home_bp', __name__, url_prefix='/home')


@blueprint.route('/index')
@login_required
def index():
    return render_template('home/index.html', segment='index')

@blueprint.route('/<template>')
@login_required
def route_template(template):
    try:
        if not template.endswith('.html'):
            template += '.html'
        
        # Detect the current page
        segment = get_segment(request)
        
        # Serve the file (if exists) from app/templates/home/FILE.html
        return render_template("home/" + template, segment=segment)
    
    except TemplateNotFound:
        return render_template('home/page-404.html'), 404
    
    except:
        return render_template('home/page-500.html'), 500

# Rotas para o blueprint home_bp
@home_bp.route('/')
@home_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('home/index.html', segment='dashboard')

@home_bp.route('/index')
@login_required
def index():
    return render_template('home/index.html', segment='index')

@home_bp.route('/index')
@login_required
def home_index():
    return render_template('home/index.html', segment='index')


# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment

    except:
        return None
