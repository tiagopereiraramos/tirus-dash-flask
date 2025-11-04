"""
Sistema de Relatórios e Analytics para API Externa Funcional
Gera relatórios detalhados, métricas e exportação de dados
"""
import logging
import json
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import io

logger = logging.getLogger(__name__)


@dataclass
class ReportConfig:
    """Configuração de relatórios"""
    # Períodos padrão
    default_period: str = "7d"  # 7d, 30d, 90d, 1y

    # Métricas a incluir
    include_performance: bool = True
    include_errors: bool = True
    include_operators: bool = True
    include_trends: bool = True

    # Exportação
    export_formats: List[str] = None  # ['json', 'csv', 'xlsx']

    def __post_init__(self):
        if self.export_formats is None:
            self.export_formats = ['json', 'csv']


@dataclass
class PerformanceMetrics:
    """Métricas de performance"""
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    cancelled_jobs: int
    timeout_jobs: int

    avg_duration: float
    min_duration: float
    max_duration: float

    success_rate: float
    failure_rate: float

    jobs_per_hour: float
    jobs_per_day: float


@dataclass
class OperatorMetrics:
    """Métricas por operadora"""
    operadora: str
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    success_rate: float
    avg_duration: float
    total_duration: float


@dataclass
class ErrorAnalysis:
    """Análise de erros"""
    error_type: str
    count: int
    percentage: float
    examples: List[str]
    last_occurrence: datetime


@dataclass
class TrendData:
    """Dados de tendência"""
    date: str
    jobs_count: int
    success_count: int
    failure_count: int
    avg_duration: float


class ReportGenerator:
    """Gerador de relatórios"""

    def __init__(self, service, config: ReportConfig = None):
        """
        Inicializa o gerador de relatórios

        Args:
            service: Instância do APIExternaFuncionalService
            config: Configuração de relatórios
        """
        self.service = service
        self.config = config or ReportConfig()

        logger.info("ReportGenerator inicializado")

    def generate_performance_report(self, period: str = None,
                                    operadora: str = None) -> Dict[str, Any]:
        """Gera relatório de performance"""
        period = period or self.config.default_period
        start_date, end_date = self._parse_period(period)

        # Obter jobs do período
        jobs = self._get_jobs_in_period(start_date, end_date, operadora)

        if not jobs:
            return self._empty_report("performance")

        # Calcular métricas
        metrics = self._calculate_performance_metrics(jobs)

        # Calcular tendências
        trends = self._calculate_trends(jobs, start_date, end_date)

        return {
            'tipo': 'performance',
            'periodo': period,
            'data_inicio': start_date.isoformat(),
            'data_fim': end_date.isoformat(),
            'operadora': operadora,
            'metricas': asdict(metrics),
            'tendencias': [asdict(trend) for trend in trends],
            'gerado_em': datetime.now().isoformat()
        }

    def generate_operator_report(self, period: str = None) -> Dict[str, Any]:
        """Gera relatório por operadora"""
        period = period or self.config.default_period
        start_date, end_date = self._parse_period(period)

        # Obter jobs do período
        jobs = self._get_jobs_in_period(start_date, end_date)

        if not jobs:
            return self._empty_report("operadoras")

        # Agrupar por operadora
        operator_metrics = self._calculate_operator_metrics(jobs)

        return {
            'tipo': 'operadoras',
            'periodo': period,
            'data_inicio': start_date.isoformat(),
            'data_fim': end_date.isoformat(),
            'operadoras': [asdict(metric) for metric in operator_metrics],
            'total_operadoras': len(operator_metrics),
            'gerado_em': datetime.now().isoformat()
        }

    def generate_error_report(self, period: str = None) -> Dict[str, Any]:
        """Gera relatório de erros"""
        period = period or self.config.default_period
        start_date, end_date = self._parse_period(period)

        # Obter jobs com erro do período
        jobs = self._get_failed_jobs_in_period(start_date, end_date)

        if not jobs:
            return self._empty_report("erros")

        # Analisar erros
        error_analysis = self._analyze_errors(jobs)

        return {
            'tipo': 'erros',
            'periodo': period,
            'data_inicio': start_date.isoformat(),
            'data_fim': end_date.isoformat(),
            'total_erros': len(jobs),
            'analise_erros': [asdict(analysis) for analysis in error_analysis],
            'gerado_em': datetime.now().isoformat()
        }

    def generate_comprehensive_report(self, period: str = None) -> Dict[str, Any]:
        """Gera relatório abrangente"""
        period = period or self.config.default_period

        # Gerar todos os relatórios
        performance = self.generate_performance_report(period)
        operators = self.generate_operator_report(period)
        errors = self.generate_error_report(period)

        # Calcular métricas gerais
        start_date, end_date = self._parse_period(period)
        jobs = self._get_jobs_in_period(start_date, end_date)

        general_metrics = {
            'periodo_total': period,
            'total_jobs': len(jobs),
            'periodo_dias': (end_date - start_date).days,
            'jobs_por_dia': len(jobs) / max((end_date - start_date).days, 1),
            'operadoras_ativas': len(set(job.operadora for job in jobs)),
            'taxa_sucesso_geral': self._calculate_success_rate(jobs)
        }

        return {
            'tipo': 'comprehensive',
            'periodo': period,
            'data_inicio': start_date.isoformat(),
            'data_fim': end_date.isoformat(),
            'metricas_gerais': general_metrics,
            'performance': performance,
            'operadoras': operators,
            'erros': errors,
            'gerado_em': datetime.now().isoformat()
        }

    def export_report(self, report: Dict[str, Any], format: str = 'json') -> bytes:
        """Exporta relatório em diferentes formatos"""
        if format == 'json':
            return self._export_json(report)
        elif format == 'csv':
            return self._export_csv(report)
        else:
            raise ValueError(f"Formato não suportado: {format}")

    def _parse_period(self, period: str) -> Tuple[datetime, datetime]:
        """Converte período em datas"""
        end_date = datetime.now()

        if period == '7d':
            start_date = end_date - timedelta(days=7)
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
        elif period == '90d':
            start_date = end_date - timedelta(days=90)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        else:
            # Tentar parse de data específica
            try:
                start_date = datetime.fromisoformat(period)
            except:
                start_date = end_date - timedelta(days=7)

        return start_date, end_date

    def _get_jobs_in_period(self, start_date: datetime, end_date: datetime,
                            operadora: str = None) -> List[Any]:
        """Obtém jobs em um período"""
        # Obter jobs do cache
        jobs = self.service.cache.get_recent_jobs(limit=10000)

        # Filtrar por período
        filtered_jobs = []
        for job in jobs:
            if job.created_at:
                try:
                    job_date = datetime.fromisoformat(
                        job.created_at.replace('Z', '+00:00'))
                    if start_date <= job_date <= end_date:
                        if operadora is None or job.operadora == operadora:
                            filtered_jobs.append(job)
                except:
                    continue

        return filtered_jobs

    def _get_failed_jobs_in_period(self, start_date: datetime, end_date: datetime) -> List[Any]:
        """Obtém jobs com falha em um período"""
        jobs = self._get_jobs_in_period(start_date, end_date)
        return [job for job in jobs if job.status == 'FAILED']

    def _calculate_performance_metrics(self, jobs: List[Any]) -> PerformanceMetrics:
        """Calcula métricas de performance"""
        total_jobs = len(jobs)
        successful_jobs = len([j for j in jobs if j.status == 'COMPLETED'])
        failed_jobs = len([j for j in jobs if j.status == 'FAILED'])
        cancelled_jobs = len([j for j in jobs if j.status == 'CANCELLED'])
        timeout_jobs = len([j for j in jobs if j.status == 'TIMEOUT'])

        # Calcular durações
        durations = []
        for job in jobs:
            if job.created_at and job.completed_at:
                try:
                    start = datetime.fromisoformat(
                        job.created_at.replace('Z', '+00:00'))
                    end = datetime.fromisoformat(
                        job.completed_at.replace('Z', '+00:00'))
                    duration = (end - start).total_seconds()
                    durations.append(duration)
                except:
                    continue

        avg_duration = sum(durations) / len(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        max_duration = max(durations) if durations else 0

        success_rate = (successful_jobs / total_jobs *
                        100) if total_jobs > 0 else 0
        failure_rate = (failed_jobs / total_jobs *
                        100) if total_jobs > 0 else 0

        # Jobs por hora/dia (baseado no período)
        period_hours = 24 * 7  # Assumindo 7 dias
        period_days = 7
        jobs_per_hour = total_jobs / period_hours
        jobs_per_day = total_jobs / period_days

        return PerformanceMetrics(
            total_jobs=total_jobs,
            successful_jobs=successful_jobs,
            failed_jobs=failed_jobs,
            cancelled_jobs=cancelled_jobs,
            timeout_jobs=timeout_jobs,
            avg_duration=avg_duration,
            min_duration=min_duration,
            max_duration=max_duration,
            success_rate=success_rate,
            failure_rate=failure_rate,
            jobs_per_hour=jobs_per_hour,
            jobs_per_day=jobs_per_day
        )

    def _calculate_operator_metrics(self, jobs: List[Any]) -> List[OperatorMetrics]:
        """Calcula métricas por operadora"""
        operator_stats = defaultdict(lambda: {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'durations': []
        })

        for job in jobs:
            operator = job.operadora
            operator_stats[operator]['total'] += 1

            if job.status == 'COMPLETED':
                operator_stats[operator]['successful'] += 1
            elif job.status == 'FAILED':
                operator_stats[operator]['failed'] += 1

            # Calcular duração
            if job.created_at and job.completed_at:
                try:
                    start = datetime.fromisoformat(
                        job.created_at.replace('Z', '+00:00'))
                    end = datetime.fromisoformat(
                        job.completed_at.replace('Z', '+00:00'))
                    duration = (end - start).total_seconds()
                    operator_stats[operator]['durations'].append(duration)
                except:
                    continue

        metrics = []
        for operator, stats in operator_stats.items():
            success_rate = (stats['successful'] / stats['total']
                            * 100) if stats['total'] > 0 else 0
            avg_duration = sum(
                stats['durations']) / len(stats['durations']) if stats['durations'] else 0
            total_duration = sum(stats['durations'])

            metrics.append(OperatorMetrics(
                operadora=operator,
                total_jobs=stats['total'],
                successful_jobs=stats['successful'],
                failed_jobs=stats['failed'],
                success_rate=success_rate,
                avg_duration=avg_duration,
                total_duration=total_duration
            ))

        # Ordenar por total de jobs
        metrics.sort(key=lambda x: x.total_jobs, reverse=True)
        return metrics

    def _analyze_errors(self, failed_jobs: List[Any]) -> List[ErrorAnalysis]:
        """Analisa erros dos jobs falhados"""
        error_types = defaultdict(lambda: {
            'count': 0,
            'examples': [],
            'last_occurrence': None
        })

        for job in failed_jobs:
            error_msg = job.error or "Erro desconhecido"

            # Categorizar erro
            if "timeout" in error_msg.lower():
                error_type = "Timeout"
            elif "connection" in error_msg.lower():
                error_type = "Erro de Conexão"
            elif "authentication" in error_msg.lower():
                error_type = "Erro de Autenticação"
            elif "validation" in error_msg.lower():
                error_type = "Erro de Validação"
            else:
                error_type = "Outros"

            error_types[error_type]['count'] += 1
            error_types[error_type]['examples'].append(error_msg[:100])

            # Manter apenas 5 exemplos
            if len(error_types[error_type]['examples']) > 5:
                error_types[error_type]['examples'] = error_types[error_type]['examples'][-5:]

            # Última ocorrência
            if job.created_at:
                try:
                    job_date = datetime.fromisoformat(
                        job.created_at.replace('Z', '+00:00'))
                    if (error_types[error_type]['last_occurrence'] is None or
                            job_date > error_types[error_type]['last_occurrence']):
                        error_types[error_type]['last_occurrence'] = job_date
                except:
                    pass

        total_errors = sum(stats['count'] for stats in error_types.values())

        analysis = []
        for error_type, stats in error_types.items():
            percentage = (stats['count'] / total_errors *
                          100) if total_errors > 0 else 0

            analysis.append(ErrorAnalysis(
                error_type=error_type,
                count=stats['count'],
                percentage=percentage,
                examples=stats['examples'],
                last_occurrence=stats['last_occurrence']
            ))

        # Ordenar por contagem
        analysis.sort(key=lambda x: x.count, reverse=True)
        return analysis

    def _calculate_trends(self, jobs: List[Any], start_date: datetime,
                          end_date: datetime) -> List[TrendData]:
        """Calcula tendências por dia"""
        daily_stats = defaultdict(lambda: {
            'jobs': 0,
            'success': 0,
            'failure': 0,
            'durations': []
        })

        for job in jobs:
            if job.created_at:
                try:
                    job_date = datetime.fromisoformat(
                        job.created_at.replace('Z', '+00:00'))
                    date_key = job_date.strftime('%Y-%m-%d')

                    daily_stats[date_key]['jobs'] += 1

                    if job.status == 'COMPLETED':
                        daily_stats[date_key]['success'] += 1
                    elif job.status == 'FAILED':
                        daily_stats[date_key]['failure'] += 1

                    # Calcular duração
                    if job.completed_at:
                        end = datetime.fromisoformat(
                            job.completed_at.replace('Z', '+00:00'))
                        duration = (end - job_date).total_seconds()
                        daily_stats[date_key]['durations'].append(duration)
                except:
                    continue

        trends = []
        for date_key, stats in daily_stats.items():
            avg_duration = sum(
                stats['durations']) / len(stats['durations']) if stats['durations'] else 0

            trends.append(TrendData(
                date=date_key,
                jobs_count=stats['jobs'],
                success_count=stats['success'],
                failure_count=stats['failure'],
                avg_duration=avg_duration
            ))

        # Ordenar por data
        trends.sort(key=lambda x: x.date)
        return trends

    def _calculate_success_rate(self, jobs: List[Any]) -> float:
        """Calcula taxa de sucesso"""
        if not jobs:
            return 0.0

        successful = len([j for j in jobs if j.status == 'COMPLETED'])
        return (successful / len(jobs)) * 100

    def _empty_report(self, report_type: str) -> Dict[str, Any]:
        """Retorna relatório vazio"""
        return {
            'tipo': report_type,
            'dados': [],
            'mensagem': 'Nenhum dado encontrado para o período especificado',
            'gerado_em': datetime.now().isoformat()
        }

    def _export_json(self, report: Dict[str, Any]) -> bytes:
        """Exporta relatório em JSON"""
        return json.dumps(report, indent=2, ensure_ascii=False, default=str).encode('utf-8')

    def _export_csv(self, report: Dict[str, Any]) -> bytes:
        """Exporta relatório em CSV"""
        output = io.StringIO()
        writer = csv.writer(output)

        # Escrever cabeçalho
        if report['tipo'] == 'performance':
            writer.writerow(['Métrica', 'Valor'])
            for key, value in report['metricas'].items():
                writer.writerow([key, value])

        elif report['tipo'] == 'operadoras':
            writer.writerow(['Operadora', 'Total Jobs', 'Sucessos',
                            'Falhas', 'Taxa Sucesso', 'Duração Média'])
            for op in report['operadoras']:
                writer.writerow([
                    op['operadora'],
                    op['total_jobs'],
                    op['successful_jobs'],
                    op['failed_jobs'],
                    f"{op['success_rate']:.2f}%",
                    f"{op['avg_duration']:.2f}s"
                ])

        elif report['tipo'] == 'erros':
            writer.writerow(['Tipo de Erro', 'Contagem',
                            'Percentual', 'Última Ocorrência'])
            for error in report['analise_erros']:
                writer.writerow([
                    error['error_type'],
                    error['count'],
                    f"{error['percentage']:.2f}%",
                    error['last_occurrence']
                ])

        return output.getvalue().encode('utf-8')


# Instância global
_report_generator: Optional[ReportGenerator] = None


def get_report_generator(service, config: ReportConfig = None) -> ReportGenerator:
    """Obtém instância global do gerador de relatórios"""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator(service, config)
    return _report_generator
