"""
Serviços de negócio para Execuções
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import joinedload

from apps import db
from apps.models import Execucao, Processo, Cliente, Operadora, Usuario
from apps.models.execucao import StatusExecucao, TipoExecucao

logger = logging.getLogger(__name__)


@dataclass
class ExecucaoFiltros:
    """Classe para organizar filtros de execuções"""
    busca: Optional[str] = None
    status: Optional[str] = None
    tipo: Optional[str] = None
    operadora_id: Optional[str] = None
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None

    @classmethod
    def from_request_args(cls, args) -> 'ExecucaoFiltros':
        """Cria instância a partir dos argumentos da requisição"""
        try:
            busca = args.get('busca', '').strip() or None
            status = args.get('status', '').strip() or None
            tipo = args.get('tipo', '').strip() or None
            operadora_id = args.get('operadora', '').strip() or None
            
            # Datas
            data_inicio = None
            data_fim = None
            
            if args.get('data_inicio'):
                try:
                    data_inicio = datetime.strptime(args.get('data_inicio'), '%Y-%m-%d')
                except ValueError:
                    pass
            
            if args.get('data_fim'):
                try:
                    data_fim = datetime.strptime(args.get('data_fim'), '%Y-%m-%d')
                    # Ajusta para fim do dia
                    data_fim = data_fim.replace(hour=23, minute=59, second=59)
                except ValueError:
                    pass

            return cls(
                busca=busca,
                status=status,
                tipo=tipo,
                operadora_id=operadora_id,
                data_inicio=data_inicio,
                data_fim=data_fim
            )
        except Exception as e:
            logger.error(f"Erro ao criar filtros: {e}")
            raise


class ExecucaoService:
    """Serviço para operações com execuções"""

    @staticmethod
    def aplicar_filtros(query, filtros: ExecucaoFiltros):
        """Aplica filtros à query de execuções"""
        try:
            if filtros.busca:
                # Busca por job_id ou dados relacionados
                query = query.join(Execucao.processo).join(Processo.cliente)
                query = query.filter(
                    or_(
                        Execucao.job_id.like(f'%{filtros.busca}%'),
                        Cliente.razao_social.like(f'%{filtros.busca}%'),
                        Cliente.cnpj.like(f'%{filtros.busca}%')
                    )
                )

            if filtros.status:
                query = query.filter(Execucao.status_execucao == filtros.status)

            if filtros.tipo:
                query = query.filter(Execucao.tipo_execucao == filtros.tipo)

            if filtros.operadora_id:
                query = query.join(Execucao.processo).join(Processo.cliente)
                query = query.filter(Cliente.operadora_id == filtros.operadora_id)

            if filtros.data_inicio:
                query = query.filter(Execucao.data_inicio >= filtros.data_inicio)

            if filtros.data_fim:
                query = query.filter(Execucao.data_inicio <= filtros.data_fim)

            return query

        except Exception as e:
            logger.error(f"Erro ao aplicar filtros: {e}")
            raise

    @staticmethod
    def obter_estatisticas(filtros: Optional[ExecucaoFiltros] = None) -> Dict[str, Any]:
        """Obtém estatísticas das execuções"""
        try:
            query = Execucao.query

            # Aplica filtros se fornecidos
            if filtros:
                query = ExecucaoService.aplicar_filtros(query, filtros)

            # Total de execuções
            total = query.count()

            # Por status
            stats_status = db.session.query(
                Execucao.status_execucao,
                func.count(Execucao.id).label('count')
            )
            
            if filtros:
                stats_status = ExecucaoService.aplicar_filtros(stats_status, filtros)
            
            stats_status = stats_status.group_by(Execucao.status_execucao).all()

            status_dict = {status: count for status, count in stats_status}

            # Por tipo
            stats_tipo = db.session.query(
                Execucao.tipo_execucao,
                func.count(Execucao.id).label('count')
            )
            
            if filtros:
                stats_tipo = ExecucaoService.aplicar_filtros(stats_tipo, filtros)
            
            stats_tipo = stats_tipo.group_by(Execucao.tipo_execucao).all()

            tipo_dict = {tipo: count for tipo, count in stats_tipo}

            # Taxa de sucesso
            concluidas = status_dict.get(StatusExecucao.CONCLUIDO.value, 0)
            taxa_sucesso = (concluidas / total * 100) if total > 0 else 0

            # Duração média das execuções concluídas
            execucoes_concluidas = query.filter(
                Execucao.status_execucao == StatusExecucao.CONCLUIDO.value,
                Execucao.data_fim.isnot(None)
            ).all()

            if execucoes_concluidas:
                duracoes = [exec.duracao_segundos for exec in execucoes_concluidas if exec.duracao_segundos]
                duracao_media = sum(duracoes) / len(duracoes) if duracoes else 0
            else:
                duracao_media = 0

            return {
                'total': total,
                'concluidas': status_dict.get(StatusExecucao.CONCLUIDO.value, 0),
                'executando': status_dict.get(StatusExecucao.EXECUTANDO.value, 0),
                'falhadas': status_dict.get(StatusExecucao.FALHOU.value, 0),
                'canceladas': status_dict.get(StatusExecucao.CANCELADO.value, 0),
                'timeout': status_dict.get(StatusExecucao.TIMEOUT.value, 0),
                'downloads': tipo_dict.get(TipoExecucao.DOWNLOAD_FATURA.value, 0),
                'uploads_sat': tipo_dict.get(TipoExecucao.UPLOAD_SAT.value, 0),
                'uploads_manual': tipo_dict.get(TipoExecucao.UPLOAD_MANUAL.value, 0),
                'taxa_sucesso': round(taxa_sucesso, 1),
                'duracao_media_segundos': round(duracao_media, 1)
            }

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            raise

    @staticmethod
    def retentar_execucao(execucao_id: str, usuario_id: str) -> Execucao:
        """
        Cria uma nova tentativa de execução baseada em uma execução anterior
        
        Args:
            execucao_id: ID da execução original
            usuario_id: ID do usuário que está retentando
            
        Returns:
            Nova execução criada
        """
        try:
            # Busca execução original
            execucao_original = Execucao.query.get(execucao_id)
            
            if not execucao_original:
                raise ValueError(f"Execução {execucao_id} não encontrada")

            # Cria nova execução
            nova_execucao = Execucao(
                processo_id=execucao_original.processo_id,
                tipo_execucao=execucao_original.tipo_execucao,
                status_execucao=StatusExecucao.EXECUTANDO.value,
                classe_rpa_utilizada=execucao_original.classe_rpa_utilizada,
                parametros_entrada=execucao_original.parametros_entrada,
                numero_tentativa=execucao_original.numero_tentativa + 1,
                executado_por_usuario_id=usuario_id
            )

            db.session.add(nova_execucao)
            db.session.commit()

            logger.info(f"Nova tentativa criada: {nova_execucao.id} (tentativa {nova_execucao.numero_tentativa})")

            return nova_execucao

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao retentar execução: {e}")
            raise

    @staticmethod
    def obter_execucoes_recentes(limite: int = 10) -> List[Execucao]:
        """Obtém as execuções mais recentes"""
        try:
            return Execucao.query.options(
                joinedload(Execucao.processo).joinedload(Processo.cliente).joinedload(Cliente.operadora),
                joinedload(Execucao.executor)
            ).order_by(desc(Execucao.data_inicio)).limit(limite).all()
        except Exception as e:
            logger.error(f"Erro ao obter execuções recentes: {e}")
            raise
