import logging
import traceback
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from sqlalchemy import and_, or_, desc
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError

from . import bp
from .forms import ProcessoForm, ProcessoFiltroForm, AprovacaoForm, CriarProcessosMensaisForm
from apps import db
from apps.models import Processo, Cliente, Operadora, Execucao, Usuario
from apps.models.processo import StatusProcesso
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
        try:
            logger.debug("Criando filtros a partir dos argumentos da requisição")
            busca = args.get('busca', '').strip() or None
            status = args.get('status', '').strip() or None
            mes_ano = args.get('mes_ano', '').strip() or None
            operadora_id = args.get('operadora', '').strip() or None

            logger.debug("Filtros extraídos - busca: %s, status: %s, mes_ano: %s, operadora_id: %s", 
                        busca, status, mes_ano, operadora_id)

            return cls(
                busca=busca,
                status=status,
                mes_ano=mes_ano,
                operadora_id=operadora_id
            )
        except Exception as e:
            logger.error("Erro ao criar filtros: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            raise

class ProcessoService:
    """Serviço para operações com processos"""

    @staticmethod
    def buscar_clientes_por_termo(termo: str) -> List[int]:
        """Busca IDs de clientes por termo de pesquisa"""
        try:
            logger.debug("Iniciando busca de clientes por termo: '%s'", termo)
            cliente_ids = set()

            # Buscar clientes por nome/cnpj
            logger.debug("Buscando clientes por nome/CNPJ")
            try:
                clientes_encontrados = Cliente.query.filter(
                    or_(
                        Cliente.razao_social.like(f'%{termo}%'),
                        Cliente.nome_sat.like(f'%{termo}%'),
                        Cliente.cnpj.like(f'%{termo}%')
                    )
                ).all()
                logger.debug("Encontrados %d clientes por nome/CNPJ", len(clientes_encontrados))

                for cliente in clientes_encontrados:
                    cliente_ids.add(cliente.id)

            except SQLAlchemyError as e:
                logger.error("Erro na query de clientes por nome/CNPJ: %s", str(e))
                raise

            # Buscar clientes por operadora
            logger.debug("Buscando clientes por operadora")
            try:
                operadoras_encontradas = Operadora.query.filter(
                    Operadora.nome.like(f'%{termo}%')
                ).all()
                logger.debug("Encontradas %d operadoras", len(operadoras_encontradas))

                for operadora in operadoras_encontradas:
                    logger.debug("Buscando clientes da operadora: %s", operadora.nome)
                    clientes_op = Cliente.query.filter_by(operadora_id=operadora.id).all()
                    logger.debug("Encontrados %d clientes para operadora %s", len(clientes_op), operadora.nome)

                    for cliente in clientes_op:
                        cliente_ids.add(cliente.id)

            except SQLAlchemyError as e:
                logger.error("Erro na query de clientes por operadora: %s", str(e))
                raise

            logger.debug("Total de IDs de clientes encontrados: %d", len(cliente_ids))
            return list(cliente_ids)

        except Exception as e:
            logger.error("Erro geral ao buscar clientes por termo '%s': %s", termo, str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            raise

    @staticmethod
    def aplicar_filtros(query, filtros: ProcessoFiltros):
        """Aplica filtros à query de processos"""
        try:
            logger.debug("Aplicando filtros à query")

            if filtros.busca:
                logger.debug("Aplicando filtro de busca: '%s'", filtros.busca)
                try:
                    cliente_ids = ProcessoService.buscar_clientes_por_termo(filtros.busca)
                    if cliente_ids:
                        logger.debug("Aplicando filtro com %d IDs de clientes", len(cliente_ids))
                        query = query.filter(Processo.cliente_id.in_(cliente_ids))
                    else:
                        logger.debug("Nenhum cliente encontrado, retornando query vazia")
                        query = query.filter(Processo.id.is_(None))
                except Exception as e:
                    logger.error("Erro ao aplicar filtro de busca: %s", str(e))
                    raise

            if filtros.status:
                logger.debug("Aplicando filtro de status: '%s'", filtros.status)
                try:
                    query = query.filter(Processo.status_processo == filtros.status)
                except Exception as e:
                    logger.error("Erro ao aplicar filtro de status: %s", str(e))
                    raise

            if filtros.mes_ano:
                logger.debug("Aplicando filtro de mês/ano: '%s'", filtros.mes_ano)
                try:
                    query = query.filter(Processo.mes_ano == filtros.mes_ano)
                except Exception as e:
                    logger.error("Erro ao aplicar filtro de mês/ano: %s", str(e))
                    raise

            if filtros.operadora_id:
                logger.debug("Aplicando filtro de operadora: '%s'", filtros.operadora_id)
                try:
                    clientes_da_operadora = Cliente.query.filter_by(
                        operadora_id=filtros.operadora_id
                    ).all()
                    logger.debug("Encontrados %d clientes para operadora", len(clientes_da_operadora))

                    if clientes_da_operadora:
                        operadora_cliente_ids = [c.id for c in clientes_da_operadora]
                        query = query.filter(Processo.cliente_id.in_(operadora_cliente_ids))
                    else:
                        logger.debug("Nenhum cliente encontrado para operadora, retornando query vazia")
                        query = query.filter(Processo.id.is_(None))
                except Exception as e:
                    logger.error("Erro ao aplicar filtro de operadora: %s", str(e))
                    raise

            logger.debug("Filtros aplicados com sucesso")
            return query

        except Exception as e:
            logger.error("Erro geral ao aplicar filtros: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            raise

@bp.route('/')
@verify_user_jwt
def index():
    """Lista todos os processos com filtros e paginação"""
    logger.info("=== INICIANDO ROTA INDEX ===")

    try:
        # Paginação
        logger.debug("Extraindo parâmetros de paginação")
        page = request.args.get('page', 1, type=int)
        per_page = 10
        logger.debug("Parâmetros de paginação - page: %d, per_page: %d", page, per_page)

        # Parâmetros de filtro
        logger.debug("Extraindo parâmetros de filtro")
        try:
            filtros = ProcessoFiltros.from_request_args(request.args)
            logger.debug("Filtros criados com sucesso")
        except Exception as e:
            logger.error("ERRO ao criar filtros: %s", str(e))
            raise

        # Query inicial
        logger.debug("Criando query inicial")
        try:
            query = Processo.query
            logger.debug("Query inicial criada")
        except Exception as e:
            logger.error("ERRO ao criar query inicial: %s", str(e))
            raise

        # Aplicar filtros
        logger.debug("Aplicando filtros à query")
        try:
            query = ProcessoService.aplicar_filtros(query, filtros)
            logger.debug("Filtros aplicados com sucesso")
        except Exception as e:
            logger.error("ERRO ao aplicar filtros: %s", str(e))
            raise

        # Ordenação
        logger.debug("Aplicando ordenação")
        try:
            query = query.order_by(Processo.data_atualizacao.desc())
            logger.debug("Ordenação aplicada")
        except Exception as e:
            logger.error("ERRO ao aplicar ordenação: %s", str(e))
            raise

        # Paginação
        logger.debug("Executando paginação")
        try:
            logger.debug("Chamando query.paginate com page=%d, per_page=%d", page, per_page)
            processos = query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            logger.debug("Paginação executada com sucesso. Total de itens: %d", processos.total if hasattr(processos, 'total') else 0)
        except Exception as e:
            logger.error("ERRO na paginação: %s", str(e))
            logger.error("Traceback da paginação: %s", traceback.format_exc())
            raise

        # Formulário
        logger.debug("Criando formulário")
        try:
            form = ProcessoFiltroForm(request.args)
            logger.debug("Formulário criado")
        except Exception as e:
            logger.error("ERRO ao criar formulário: %s", str(e))
            raise

        # Renderizar template
        logger.debug("Renderizando template")
        try:
            result = render_template(
                'processos/index.html',
                processos=processos,
                form=form
            )
            logger.info("=== ROTA INDEX FINALIZADA COM SUCESSO ===")
            return result
        except Exception as e:
            logger.error("ERRO ao renderizar template: %s", str(e))
            raise

    except Exception as e:
        logger.error("=== ERRO GERAL NA ROTA INDEX ===")
        logger.error("Tipo da exceção: %s", type(e).__name__)
        logger.error("Mensagem da exceção: %s", str(e))
        logger.error("Representação da exceção: %r", e)
        logger.error("Traceback completo: %s", traceback.format_exc())

        # Tentar diferentes formas de log para identificar o problema
        try:
            logger.error("Tentativa 1 - str(e): %s", str(e))
        except Exception as log_err1:
            logger.error("Erro no log tentativa 1: %s", str(log_err1))

        try:
            logger.error("Tentativa 2 - repr(e): %r", e)
        except Exception as log_err2:
            logger.error("Erro no log tentativa 2: %s", str(log_err2))

        try:
            logger.error("Tentativa 3 - format: Erro ao carregar processos: {}".format(str(e)))
        except Exception as log_err3:
            logger.error("Erro no log tentativa 3: %s", str(log_err3))

        flash('Erro ao carregar processos. Tente novamente.', 'danger')
        return redirect(url_for('home_blueprint.index'))

# Mantendo as outras rotas sem alteração por enquanto, focando no debug da rota principal
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

            processo_existente = db.session.query(Processo).filter(
                and_(
                    Processo.cliente_id == form.cliente_id.data,
                    Processo.mes_ano == form.mes_ano.data
                )
            ).first()

            if processo_existente:
                flash('Já existe um processo para este cliente no mês/ano informado.', 'danger')
                return render_template('processos/form.html', form=form, titulo="Novo Processo")

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

            logger.info("Processo criado: %s - %s - %s", 
                       str(processo.id), 
                       str(processo.cliente.razao_social), 
                       str(processo.mes_ano))
            flash('Processo criado com sucesso!', 'success')

            return redirect(url_for('processos_bp.visualizar', id=processo.id))

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar processo: %s", str(e))
            flash('Erro ao criar processo. Tente novamente.', 'danger')

    return render_template('processos/form.html', form=form, titulo="Novo Processo")

# Adicione um endpoint de teste para verificar se o problema está na configuração do logger
@bp.route('/test-log')
@verify_user_jwt
def test_log():
    """Endpoint para testar diferentes tipos de log"""
    try:
        # Testes de diferentes tipos de log
        logger.info("Teste de log INFO")
        logger.debug("Teste de log DEBUG")
        logger.warning("Teste de log WARNING")

        # Simular uma exceção para testar o tratamento
        try:
            raise ValueError("Teste de exceção com %s formatação")
        except Exception as e:
            logger.error("Teste 1 - str(e): %s", str(e))
            logger.error("Teste 2 - repr(e): %r", e)
            logger.error("Teste 3 - format: {}".format(str(e)))
            logger.error("Teste 4 - f-string: %s", f"Exceção: {str(e)}")

        return jsonify({"status": "success", "message": "Testes de log executados"})

    except Exception as e:
        logger.error("Erro no teste de log: %s", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route('/criar-processos-mensais', methods=['GET', 'POST'])
@verify_user_jwt
def criar_processos_mensais():
    """Criar processos mensais em massa"""
    form = CriarProcessosMensaisForm()

    if form.validate_on_submit():
        try:
            if not Processo.validar_formato_mes_ano(form.mes_ano.data):
                flash('Formato de mês/ano inválido. Use MM/AAAA.', 'danger')
                return render_template('processos/criar_mensais.html', form=form)

            # Query base para clientes ativos
            query_clientes = Cliente.query.filter(Cliente.status_ativo == True)

            # Filtrar por operadora se especificado
            if form.operadora_id.data:
                query_clientes = query_clientes.filter(Cliente.operadora_id == form.operadora_id.data)

            clientes = query_clientes.all()

            if not clientes:
                flash('Nenhum cliente encontrado para criar processos.', 'warning')
                return render_template('processos/criar_mensais.html', form=form)

            processos_criados = 0
            processos_existentes = 0

            for cliente in clientes:
                # Verificar se já existe processo para este cliente no mês/ano
                processo_existente = Processo.query.filter(
                    and_(
                        Processo.cliente_id == cliente.id,
                        Processo.mes_ano == form.mes_ano.data
                    )
                ).first()

                if processo_existente:
                    processos_existentes += 1
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

            mensagem = f"Processos criados: {processos_criados}"
            if processos_existentes > 0:
                mensagem += f" | Já existiam: {processos_existentes}"

            flash(mensagem, 'success')
            return redirect(url_for('processos_bp.index'))

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar processos mensais: %s", str(e))
            flash('Erro ao criar processos. Tente novamente.', 'danger')

    return render_template('processos/criar_mensais.html', form=form)

# Adicione também um endpoint para verificar o estado do banco
@bp.route('/visualizar/<id>')
@verify_user_jwt
def visualizar(id):
    """Visualizar detalhes de um processo"""
    try:
        processo = Processo.query.options(
            joinedload(Processo.cliente).joinedload(Cliente.operadora)
        ).get_or_404(id)
        
        return render_template('processos/detalhes.html', processo=processo)
    
    except Exception as e:
        logger.error("Erro ao visualizar processo: %s", str(e))
        flash('Erro ao carregar processo. Tente novamente.', 'danger')
        return redirect(url_for('processos_bp.index'))

@bp.route('/editar/<id>', methods=['GET', 'POST'])
@verify_user_jwt
def editar(id):
    """Editar um processo"""
    try:
        processo = Processo.query.get_or_404(id)
        form = ProcessoForm(obj=processo)
        
        if form.validate_on_submit():
            try:
                if not Processo.validar_formato_mes_ano(form.mes_ano.data):
                    flash('Formato de mês/ano inválido. Use MM/AAAA.', 'danger')
                    return render_template('processos/form.html', form=form, titulo="Editar Processo")

                # Verificar se não há outro processo com mesmo cliente/mes_ano (exceto o atual)
                processo_existente = db.session.query(Processo).filter(
                    and_(
                        Processo.cliente_id == form.cliente_id.data,
                        Processo.mes_ano == form.mes_ano.data,
                        Processo.id != processo.id
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

                logger.info("Processo editado: %s - %s - %s", 
                           str(processo.id), 
                           str(processo.cliente.razao_social), 
                           str(processo.mes_ano))
                flash('Processo atualizado com sucesso!', 'success')

                return redirect(url_for('processos_bp.visualizar', id=processo.id))

            except Exception as e:
                db.session.rollback()
                logger.error("Erro ao editar processo: %s", str(e))
                flash('Erro ao editar processo. Tente novamente.', 'danger')

        return render_template('processos/form.html', form=form, titulo="Editar Processo")
    
    except Exception as e:
        logger.error("Erro ao carregar processo para edição: %s", str(e))
        flash('Erro ao carregar processo. Tente novamente.', 'danger')
        return redirect(url_for('processos_bp.index'))

@bp.route('/test-db')
@verify_user_jwt
def test_db():
    """Endpoint para testar conexão com o banco"""
    try:
        logger.info("Testando conexão com banco de dados")

        # Teste simples de contagem
        count_processos = db.session.query(Processo).count()
        logger.info("Contagem de processos: %d", count_processos)

        count_clientes = db.session.query(Cliente).count()
        logger.info("Contagem de clientes: %d", count_clientes)

        count_operadoras = db.session.query(Operadora).count()
        logger.info("Contagem de operadoras: %d", count_operadoras)

        return jsonify({
            "status": "success", 
            "data": {
                "processos": count_processos,
                "clientes": count_clientes,
                "operadoras": count_operadoras
            }
        })

    except Exception as e:
        logger.error("Erro no teste de banco: %s", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500