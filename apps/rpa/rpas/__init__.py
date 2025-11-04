"""
Módulo de RPAs - Implementações específicas por operadora
"""

from .embratel_rpa import EmbratelRPA
from .digitalnet_rpa import DigitalnetRPA
from .vivo_rpa import VivoRPA
from .oi_rpa import OiRPA
from .sat_rpa import SatRPA

__all__ = [
    'EmbratelRPA',
    'DigitalnetRPA',
    'VivoRPA',
    'OiRPA',
    'SatRPA'
]
