"""Bazi analysis package for Chinese astrology calculations."""

# Import key classes for easy access
from .main import BaziChartAnalyseFrame

# Make submodules available
from . import core
from . import analysis
from . import utils

# Version information
__version__ = "0.1"

# Re-export BaziChartAnalyseFrame for convenience
from .main import BaziChartAnalyseFrame
