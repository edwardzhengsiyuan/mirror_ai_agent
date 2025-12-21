# analysis/base_analyser.py

from abc import ABC, abstractmethod

from ..core import BaziChart
from ..utils import LogHelper


class BaseAnalyser(ABC):
    def __init__(self, bazi_chart: BaziChart, log_helper: LogHelper):
        self._bazi_chart = bazi_chart
        self._log_helper = log_helper

    @abstractmethod
    def analyse(self):
        pass