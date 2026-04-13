from typing import Dict, Any
from ..base_analyser import BaseAnalyser
from ...core.bazi_chart import BaziChart
from ...core import Gan, Zhi, Zhu, Wuxing
from ...utils import LogHelper
from .daily_trend_chart import DailyTrendChart
from ..power.bazi_power_chart import BaziPowerChart
from ..power.power_transformer import PowerTransformer
from ..hehua.hehua_analysis import HehuaAnalysis
from lunar_python import Solar

class DailyFortuneAnalyser(BaseAnalyser):
    def __init__(self, bazi_chart: BaziChart, log_helper: LogHelper):
        super().__init__(bazi_chart, log_helper)

    def analyse(self):
        """
        Required by BaseAnalyser. 
        For DailyFortuneAnalyser, use analyse_daily_score with specific parameters.
        """
        raise NotImplementedError("Please use analyse_daily_score(year, month, day, xi_ji_weights) instead.")
        
    def analyse_daily_score(self, year: int, month: int, day: int, xi_ji_weights: Dict[str, Dict[str, float]]) -> float:
        """
        Calculate daily fortune score.
        
        Args:
            year, month, day: Target date.
            xi_ji_weights: Dictionary of weights, e.g.,
                {"喜": {"木": 30, "火": 70}, "忌": {"金": 50, "水": 20, "土": 30}}
                
        Returns:
            float: Score between 0 and 100.
        """
        # 1. Prepare DailyTrendChart
        trend_chart = self._create_trend_chart(year, month, day)
        
        # 2. Analyze Forces (Hehua)
        # We need a log helper that doesn't output to terminal for internal calculations if preferred,
        # but here we reuse the existing one.
        hehua_analyser = HehuaAnalysis(trend_chart, self._log_helper)
        hehua_check_results, hehua_forces = hehua_analyser.analyse()
        
        # 3. Calculate Power
        # Initialize BaziPowerChart
        power_chart = BaziPowerChart(trend_chart, hehua_forces)
        
        # Transform Power
        transformer = PowerTransformer(trend_chart, power_chart, hehua_forces, self._log_helper)
        transformed_chart = transformer.transform()
        
        # Calculate final powers
        transformed_chart.calculate_powers()
        
        # 4. Calculate Score
        wuxing_proportions = transformed_chart.wuxing_proportions
        score = self._calculate_score(wuxing_proportions, xi_ji_weights)
        
        return score
    
    def _create_trend_chart(self, year: int, month: int, day: int) -> DailyTrendChart:
        # Calculate Pillars for the date
        solar = Solar.fromYmdHms(year, month, day, 12, 0, 0)
        lunar = solar.getLunar()
        
        # Liunian
        liunian_gan = Gan.from_chinese(lunar.getYearGan())
        liunian_zhi = Zhi.from_chinese(lunar.getYearZhi())
        liunian_zhu = self._create_simple_zhu(liunian_gan, liunian_zhi)
        
        # Liuyue
        liuyue_gan = Gan.from_chinese(lunar.getMonthGan())
        liuyue_zhi = Zhi.from_chinese(lunar.getMonthZhi())
        liuyue_zhu = self._create_simple_zhu(liuyue_gan, liuyue_zhi)
        
        # Liuri
        liuri_gan = Gan.from_chinese(lunar.getDayGan())
        liuri_zhi = Zhi.from_chinese(lunar.getDayZhi())
        liuri_zhu = self._create_simple_zhu(liuri_gan, liuri_zhi)
        
        # Dayun
        current_dayun = self._get_current_dayun(year)
        if not current_dayun:
            # Fallback or error? Assuming BaziChart has dayun calculated.
            # If no dayun (e.g. too young/old or error), maybe use Year as fallback?
            # Or raise error. Let's use Liunian as fallback for robustness but log warning.
            self._log_helper.warning(f"Could not find Dayun for year {year}. Using Liunian as Dayun.")
            dayun_zhu = liunian_zhu
        else:
            ganzhi = current_dayun.getGanZhi()
            dayun_gan = Gan.from_chinese(ganzhi[0])
            dayun_zhi = Zhi.from_chinese(ganzhi[1])
            dayun_zhu = self._create_simple_zhu(dayun_gan, dayun_zhi)
            
        return DailyTrendChart(dayun_zhu, liunian_zhu, liuyue_zhu, liuri_zhu, self._bazi_chart)

    def _create_simple_zhu(self, gan: Gan, zhi: Zhi):
        # Helper to create a Zhu-like object with .gan and .zhi properties that mimic BaziChartGan/Zhi structure minimally
        # But DailyTrendChart expects objects that have ._gan and ._zhi attributes or similar?
        # No, DailyTrendChart constructor takes Zhu objects which wrapper BaziChartGan/Zhi.
        # But here I need to pass something that DailyTrendChart can use to create its internal BaziChartGan/Zhi.
        # DailyTrendChart.__init__ takes: dayun: Zhu, ...
        # And uses dayun.gan._gan and dayun.zhi._zhi.
        
        class SimpleElement:
            def __init__(self, value):
                self._gan = value if isinstance(value, Gan) else None
                self._zhi = value if isinstance(value, Zhi) else None
                
        class SimpleZhu:
            def __init__(self, g, z):
                self.gan = SimpleElement(g)
                self.zhi = SimpleElement(z)
                
        return SimpleZhu(gan, zhi)

    def _get_current_dayun(self, year):
        if hasattr(self._bazi_chart, 'dayun'):
            for dayun in self._bazi_chart.dayun:
                start_year = dayun.getStartYear()
                end_year = dayun.getEndYear()
                if start_year <= year < end_year:
                    return dayun
        return None

    def _calculate_score(self, proportions: Dict[Wuxing, float], weights: Dict[str, Dict[str, float]]) -> float:
        # Weights format: {"喜": {"木": 30}, "忌": {"火": 50}} (Keys are Chinese strings)
        
        score_xi = 0.0
        score_ji = 0.0
        
        xi_weights = weights.get("喜", {})
        ji_weights = weights.get("忌", {})
        
        wuxing_map = {
            "木": Wuxing.MU,
            "火": Wuxing.HUO,
            "土": Wuxing.TU,
            "金": Wuxing.JIN,
            "水": Wuxing.SHUI
        }
        
        # Calculate Contribution from Xi
        for wx_str, weight in xi_weights.items():
            wx_enum = wuxing_map.get(wx_str)
            if wx_enum:
                # proportion is 0.0 to 1.0. weight is e.g. 30.
                score_xi += proportions.get(wx_enum, 0) * weight
                
        # Calculate Contribution from Ji
        for wx_str, weight in ji_weights.items():
            wx_enum = wuxing_map.get(wx_str)
            if wx_enum:
                score_ji += proportions.get(wx_enum, 0) * weight
                
        # Raw Score = Xi - Ji.
        raw_score = score_xi - score_ji
        
        # Calculate theoretical bounds to normalize the score
        total_xi = sum(xi_weights.values())
        total_ji = sum(ji_weights.values())
        
        # Theoretical Max (100% power in Xi) = total_xi
        # Theoretical Min (100% power in Ji) = -total_ji
        max_raw = total_xi
        min_raw = -total_ji
        raw_range = max_raw - min_raw
        
        if raw_range == 0:
            return 75.0  # Default to middle of 50-100 if no weights provided
            
        # Normalize raw_score to [0, 1] relative to the range [min_raw, max_raw]
        normalized_ratio = (raw_score - min_raw) / raw_range
        
        # Map [0, 1] to [50, 100]
        final_score = 50.0 + normalized_ratio * 50.0
        
        return max(50.0, min(100.0, final_score))

