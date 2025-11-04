"""
RPA Oi - Implementação específica para Oi
"""

from ..base import RPABase, ParametrosEntradaPadrao, ResultadoSaidaPadrao, StatusExecucaoRPA
from datetime import datetime


class OiRPA(RPABase):
    """RPA específico para Oi"""

    def __init__(self):
        super().__init__()
        self.nome_rpa = "OiRPA"

    def executar_download(self, parametros: ParametrosEntradaPadrao) -> ResultadoSaidaPadrao:
        """Executa download de fatura Oi"""
        return ResultadoSaidaPadrao(
            sucesso=False,
            status=StatusExecucaoRPA.ERRO,
            mensagem="OiRPA não implementado ainda",
            timestamp_inicio=datetime.now(),
            timestamp_fim=datetime.now()
        )

    def executar_upload_sat(self, parametros: ParametrosEntradaPadrao) -> ResultadoSaidaPadrao:
        """Executa upload de fatura para SAT"""
        return ResultadoSaidaPadrao(
            sucesso=False,
            status=StatusExecucaoRPA.ERRO,
            mensagem="OiRPA não suporta upload para SAT",
            timestamp_inicio=datetime.now(),
            timestamp_fim=datetime.now()
        )
