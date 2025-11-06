import logging
import traceback
import queue
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, Response, stream_with_context
from sqlalchemy import and_, or_, desc
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError

from . import bp
from .forms import ProcessoForm, ProcessoFiltroForm, AprovacaoForm, CriarProcessosMensaisForm
from apps import db
from apps.models import Processo, Cliente, Operadora, Execucao, Usuario
from apps.models.processo import StatusProcesso
from apps.authentication.util import verify_user_jwt
from apps.api_externa.services import APIExternaService

logger = logging.getLogger(__name__)

sse_queues = []

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
            joinedload(Processo.cliente).joinedload(Cliente.operadora),
            joinedload(Processo.aprovador)
        ).get_or_404(id)
        
        # Carregar execuções relacionadas ao processo
        execucoes = processo.execucoes.all()
        
        return render_template('processos/detalhes.html', processo=processo, execucoes=execucoes)
    
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

@bp.route('/enviar-sat/<id>', methods=['POST'])
@verify_user_jwt
def enviar_sat(id):
    """Enviar processo para SAT"""
    try:
        processo = Processo.query.get_or_404(id)
        
        if not processo.pode_enviar_sat:
            return jsonify({'success': False, 'message': 'Processo não pode ser enviado para SAT no status atual'}), 400
        
        processo.enviar_para_sat()
        db.session.commit()
        
        logger.info("Processo enviado para SAT: %s", str(processo.id))
        return jsonify({'success': True, 'message': 'Processo enviado para SAT com sucesso'})
        
    except Exception as e:
        db.session.rollback()
        logger.error("Erro ao enviar processo para SAT: %s", str(e))
        return jsonify({'success': False, 'message': 'Erro ao enviar processo para SAT'}), 500

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


@bp.route('/executar-download/<id>', methods=['POST'])
@verify_user_jwt
def executar_download(id):
    """
    Executa o download da fatura via API Externa (Operadora)
    
    Cria um job assíncrono na API externa para download de faturas.
    O job_id retornado pode ser usado para consultar o status.
    """
    try:
        processo = Processo.query.get_or_404(id)
        
        if processo.status_processo != StatusProcesso.AGUARDANDO_DOWNLOAD.value:
            return jsonify({
                'success': False, 
                'message': 'Processo não está aguardando download'
            }), 400
        
        logger.info(f"Iniciando execução de download para processo {id}")
        
        api_service = APIExternaService()
        job_response = api_service.executar_operadora(processo)
        
        logger.info(f"Job criado com sucesso: {job_response.job_id}")
        
        return jsonify({
            'success': True,
            'message': f'Download iniciado com sucesso',
            'job_id': job_response.job_id,
            'status': job_response.status
        })
        
    except Exception as e:
        logger.error(f"Erro ao executar download: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Erro ao executar download: {str(e)}'
        }), 500


@bp.route('/executar-upload-sat/<id>', methods=['POST'])
@verify_user_jwt
def executar_upload_sat(id):
    """
    Executa o upload para SAT via API Externa
    
    Diferente de /enviar-sat (que apenas marca como enviado),
    esta rota realmente executa o RPA de upload via API Externa.
    """
    try:
        processo = Processo.query.get_or_404(id)
        
        if processo.status_processo != StatusProcesso.AGUARDANDO_ENVIO_SAT.value:
            return jsonify({
                'success': False,
                'message': 'Processo não está aguardando envio para SAT'
            }), 400
        
        logger.info(f"Iniciando execução de upload SAT para processo {id}")
        
        api_service = APIExternaService()
        job_response = api_service.executar_sat(processo)
        
        logger.info(f"Job SAT criado com sucesso: {job_response.job_id}")
        
        return jsonify({
            'success': True,
            'message': 'Upload para SAT iniciado com sucesso',
            'job_id': job_response.job_id,
            'status': job_response.status
        })
        
    except Exception as e:
        logger.error(f"Erro ao executar upload SAT: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao executar upload SAT: {str(e)}'
        }), 500


@bp.route('/consultar-status-job/<job_id>', methods=['GET'])
@verify_user_jwt
def consultar_status_job(job_id):
    """
    Consulta o status de um job na API Externa
    
    Retorna informações atualizadas sobre a execução do job,
    incluindo status, progresso e mensagens.
    """
    try:
        logger.info(f"Consultando status do job {job_id}")
        
        api_service = APIExternaService()
        job_status = api_service.consultar_status(job_id)
        
        return jsonify({
            'success': True,
            'job_id': job_status.job_id,
            'status': job_status.status,
            'message': job_status.message,
            'progress': job_status.progress,
            'created_at': job_status.created_at,
            'updated_at': job_status.updated_at,
            'error': job_status.error
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Erro ao consultar status do job: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao consultar status: {str(e)}'
        }), 500


@bp.route('/health-api-externa', methods=['GET'])
@verify_user_jwt  
def health_api_externa():
    """
    Verifica se a API Externa está funcionando
    """
    try:
        api_service = APIExternaService()
        is_healthy = api_service.health_check()
        
        return jsonify({
            'success': True,
            'api_externa_online': is_healthy,
            'url': api_service.base_url
        })
        
    except Exception as e:
        logger.error(f"Erro ao verificar saúde da API Externa: {str(e)}")
        return jsonify({
            'success': False,
            'api_externa_online': False,
            'message': str(e)
        }), 500


@bp.route('/aprovar/<id>', methods=['POST'])
@verify_user_jwt
def aprovar(id):
    """
    Aprova um processo e move para AGUARDANDO_ENVIO_SAT
    """
    try:
        from flask_login import current_user
        
        processo = Processo.query.get_or_404(id)
        
        if not processo.pode_ser_aprovado:
            return jsonify({
                'success': False,
                'message': 'Processo não pode ser aprovado no status atual'
            }), 400
        
        observacoes = request.form.get('observacoes', request.json.get('observacoes', '') if request.is_json else '')
        
        processo.aprovar(current_user.id, observacoes)
        db.session.commit()
        
        logger.info(f"Processo {id} aprovado por usuário {current_user.id}")
        
        enviar_evento_sse({
            'type': 'status_changed',
            'processo_id': str(id),
            'status_antigo': StatusProcesso.AGUARDANDO_APROVACAO.value,
            'status_novo': StatusProcesso.AGUARDANDO_ENVIO_SAT.value
        })
        
        return jsonify({
            'success': True,
            'message': 'Processo aprovado com sucesso',
            'status_novo': processo.status_processo
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao aprovar processo {id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao aprovar processo: {str(e)}'
        }), 500


@bp.route('/rejeitar/<id>', methods=['POST'])
@verify_user_jwt
def rejeitar(id):
    """
    Rejeita um processo e volta para AGUARDANDO_DOWNLOAD
    """
    try:
        from flask_login import current_user
        
        processo = Processo.query.get_or_404(id)
        
        if not processo.pode_ser_aprovado:
            return jsonify({
                'success': False,
                'message': 'Processo não pode ser rejeitado no status atual'
            }), 400
        
        observacoes = request.form.get('observacoes', request.json.get('observacoes', '') if request.is_json else '')
        
        if not observacoes:
            return jsonify({
                'success': False,
                'message': 'Motivo da rejeição é obrigatório'
            }), 400
        
        processo.rejeitar(observacoes)
        db.session.commit()
        
        logger.info(f"Processo {id} rejeitado por usuário {current_user.id}: {observacoes}")
        
        enviar_evento_sse({
            'type': 'status_changed',
            'processo_id': str(id),
            'status_antigo': StatusProcesso.AGUARDANDO_APROVACAO.value,
            'status_novo': StatusProcesso.AGUARDANDO_DOWNLOAD.value
        })
        
        return jsonify({
            'success': True,
            'message': 'Processo rejeitado. Voltou para aguardando download.',
            'status_novo': processo.status_processo
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao rejeitar processo {id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao rejeitar processo: {str(e)}'
        }), 500


@bp.route('/fatura-dados/<id>', methods=['GET'])
@verify_user_jwt
def fatura_dados(id):
    """
    Retorna os dados da fatura para visualização
    """
    try:
        processo = Processo.query.get_or_404(id)
        
        if not processo.tem_fatura_para_visualizar:
            return jsonify({
                'success': False,
                'message': 'Fatura não disponível para visualização'
            }), 404
        
        return jsonify({
            'success': True,
            'url_fatura': processo.url_fatura,
            'caminho_s3': processo.caminho_s3_fatura,
            'valor': float(processo.valor_fatura) if processo.valor_fatura else None,
            'data_vencimento': processo.data_vencimento.strftime('%d/%m/%Y') if processo.data_vencimento else None
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados da fatura: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao buscar fatura: {str(e)}'
        }), 500


@bp.route('/sse/status', methods=['GET'])
def sse_status():
    """
    Server-Sent Events (SSE) para monitoramento em tempo real de processos e jobs
    
    Eventos enviados:
    - job_started: Quando um job RPA é iniciado
    - job_progress: Progresso do job (0-100%)
    - job_completed: Job concluído com sucesso
    - job_failed: Job falhou
    - status_changed: Status do processo mudou
    """
    def event_stream():
        messages = queue.Queue()
        sse_queues.append(messages)
        
        try:
            while True:
                try:
                    msg = messages.get(timeout=30)
                    
                    event_type = msg.get('type', 'message')
                    data = json.dumps(msg)
                    
                    yield f"event: {event_type}\ndata: {data}\n\n"
                    
                except queue.Empty:
                    yield f": keepalive\n\n"
                    
        finally:
            sse_queues.remove(messages)
    
    return Response(
        stream_with_context(event_stream()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


def enviar_evento_sse(evento: Dict[str, Any]):
    """
    Envia evento para todos os clientes conectados via SSE
    """
    for q in sse_queues:
        try:
            q.put_nowait(evento)
        except queue.Full:
            pass


def criar_processos_mensais_automatico(mes_ano: Optional[str] = None, operadora_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Cria processos mensais automaticamente (usado por agendamentos)
    
    Args:
        mes_ano: Mês/ano no formato MM/AAAA (padrão: mês atual)
        operadora_id: ID da operadora para filtrar (opcional)
    
    Returns:
        Dicion ário com resultado da operação
    """
    try:
        # Usar mês/ano atual se não especificado
        if not mes_ano:
            agora = datetime.now()
            mes_ano = agora.strftime('%m/%Y')
        
        # Validar formato
        if not Processo.validar_formato_mes_ano(mes_ano):
            return {
                'success': False,
                'error': 'Formato de mês/ano inválido. Use MM/AAAA.',
                'processos_criados': 0,
                'processos_existentes': 0
            }
        
        # Query base para clientes ativos
        query_clientes = Cliente.query.filter(Cliente.status_ativo == True)
        
        # Filtrar por operadora se especificado
        if operadora_id:
            query_clientes = query_clientes.filter(Cliente.operadora_id == operadora_id)
        
        clientes = query_clientes.all()
        
        if not clientes:
            return {
                'success': False,
                'error': 'Nenhum cliente ativo encontrado',
                'processos_criados': 0,
                'processos_existentes': 0
            }
        
        processos_criados = 0
        processos_existentes = 0
        
        for cliente in clientes:
            # Verificar se já existe processo para este cliente no mês/ano
            processo_existente = Processo.query.filter(
                and_(
                    Processo.cliente_id == cliente.id,
                    Processo.mes_ano == mes_ano
                )
            ).first()
            
            if processo_existente:
                processos_existentes += 1
                continue
            
            # Criar novo processo
            processo = Processo(
                cliente_id=cliente.id,
                mes_ano=mes_ano,
                status_processo=StatusProcesso.AGUARDANDO_DOWNLOAD.value,
                criado_automaticamente=True
            )
            
            db.session.add(processo)
            processos_criados += 1
        
        db.session.commit()
        
        logger.info(f"Processos mensais criados automaticamente: {processos_criados} (existentes: {processos_existentes})")
        
        return {
            'success': True,
            'processos_criados': processos_criados,
            'processos_existentes': processos_existentes,
            'mes_ano': mes_ano
        }
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar processos mensais automaticamente: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'processos_criados': 0,
            'processos_existentes': 0
        }