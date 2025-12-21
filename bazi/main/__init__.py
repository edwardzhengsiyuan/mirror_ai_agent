# main/__init__.py

import sys
import os

# Add parent directory to path so relative imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

"""Main analysis interface modules."""

# Export the main analysis class
from .bazi_chart_analyse_frame import BaziChartAnalyseFrame
