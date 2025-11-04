"""
RPA Digitalnet - Implementação específica para Digitalnet
"""

from ..base import RPABase, ParametrosEntradaPadrao, ResultadoSaidaPadrao, StatusExecucaoRPA
from datetime import datetime


class DigitalnetRPA(RPABase):
    """RPA específico para Digitalnet"""

    def __init__(self):
        super().__init__()
        self.nome_rpa = "DigitalnetRPA"

    def executar_download(self, parametros: ParametrosEntradaPadrao) -> ResultadoSaidaPadrao:
        """Executa download de fatura Digitalnet"""
        return ResultadoSaidaPadrao(
            sucesso=False,
            status=StatusExecucaoRPA.ERRO,
            mensagem="DigitalnetRPA não implementado ainda",
            timestamp_inicio=datetime.now(),
            timestamp_fim=datetime.now()
        )

    def executar_upload_sat(self, parametros: ParametrosEntradaPadrao) -> ResultadoSaidaPadrao:
        """Executa upload de fatura para SAT"""
        return ResultadoSaidaPadrao(
            sucesso=False,
            status=StatusExecucaoRPA.ERRO,
            mensagem="DigitalnetRPA não suporta upload para SAT",
            timestamp_inicio=datetime.now(),
            timestamp_fim=datetime.now()
        )
