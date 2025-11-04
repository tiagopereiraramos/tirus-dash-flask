from flask import Blueprint, render_template, request
from apps.processos.forms import ProcessoFiltroForm
from apps.models import Processo
from apps import db

bp = Blueprint('processos', __name__, url_prefix='/processos')


@bp.route('/listar', methods=['GET', 'POST'])
def listar_processos():
    form = ProcessoFiltroForm()
    processos = []

    if form.validate_on_submit():
        filtros = {
            'busca': form.busca.data,
            'status': form.status.data,
            'mes_ano': form.mes_ano.data,
            'operadora': form.operadora.data
        }

        query = db.session.query(Processo)

        if filtros['busca']:
            query = query.filter(
                Processo.cliente_razao_social.ilike(f"%{filtros['busca']}%"))

        if filtros['status']:
            query = query.filter(Processo.status == filtros['status'])

        if filtros['mes_ano']:
            query = query.filter(Processo.mes_ano == filtros['mes_ano'])

        if filtros['operadora']:
            query = query.filter(Processo.operadora_id == filtros['operadora'])

        processos = query.all()

    return render_template('processos/listar.html', form=form, processos=processos)
