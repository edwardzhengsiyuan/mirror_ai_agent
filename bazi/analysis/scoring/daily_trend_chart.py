from typing import List, Optional
from ...core.bazi_chart import BaziChart, BaziChartGan, BaziChartZhi, Zhu
from ...core import Gan, Zhi

class DailyTrendChart:
    """
    A mocked BaziChart for Daily Fortune Analysis.
    Structure: [DaYun, LiuNian, LiuYue, LiuRi] mapped to [Year, Month, Day, Hour].
    """
    def __init__(self, dayun: Zhu, liunian: Zhu, liuyue: Zhu, liuri: Zhu, original_chart: BaziChart):
        self.original_chart = original_chart
        self.without_time = False
        
        # Map inputs to standard BaziChart properties
        # Index 0: DaYun -> Year
        # Index 1: LiuNian -> Month
        # Index 2: LiuYue -> Day
        # Index 3: LiuRi -> Hour
        
        # We need to wrap raw Gan/Zhi into BaziChartGan/BaziChartZhi
        # BaziChartGan/Zhi need a day_gan for Shishen calculation. 
        # We should use the ORIGINAL chart's day_gan for Shishen perspective.
        self.day_gan_ref = original_chart.day_gan._gan
        self.day_gan_element = original_chart.day_gan # Keep the original day gan element for reference if needed
        
        self._year_gan = BaziChartGan(dayun.gan._gan, self.day_gan_ref, 0)
        self._year_zhi = BaziChartZhi(dayun.zhi._zhi, self.day_gan_ref, 0)
        self._year_zhu = Zhu(self._year_gan, self._year_zhi)
        
        self._month_gan = BaziChartGan(liunian.gan._gan, self.day_gan_ref, 1)
        self._month_zhi = BaziChartZhi(liunian.zhi._zhi, self.day_gan_ref, 1)
        self._month_zhu = Zhu(self._month_gan, self._month_zhi)
        
        self._day_gan = BaziChartGan(liuyue.gan._gan, self.day_gan_ref, 2)
        self._day_zhi = BaziChartZhi(liuyue.zhi._zhi, self.day_gan_ref, 2)
        self._day_zhu = Zhu(self._day_gan, self._day_zhi)
        
        self._hour_gan = BaziChartGan(liuri.gan._gan, self.day_gan_ref, 3)
        self._hour_zhi = BaziChartZhi(liuri.zhi._zhi, self.day_gan_ref, 3)
        self._hour_zhu = Zhu(self._hour_gan, self._hour_zhi)
        
        self._gan_list = [self._year_gan, self._month_gan, self._day_gan, self._hour_gan]
        self._zhi_list = [self._year_zhi, self._month_zhi, self._day_zhi, self._hour_zhi]
        self._zhu_list = [self._year_zhu, self._month_zhu, self._day_zhu, self._hour_zhu]
        
    @property
    def year_gan(self): return self._year_gan
    @property
    def year_zhi(self): return self._year_zhi
    @property
    def month_gan(self): return self._month_gan
    @property
    def month_zhi(self): return self._month_zhi
    @property
    def day_gan(self): return self._day_gan
    @property
    def day_zhi(self): return self._day_zhi
    @property
    def hour_gan(self): return self._hour_gan
    @property
    def hour_zhi(self): return self._hour_zhi
    
    @property
    def gan_list(self): return self._gan_list
    @property
    def zhi_list(self): return self._zhi_list
    @property
    def zhu_list(self): return self._zhu_list

    @property
    def year_zhu(self): return self._year_zhu
    @property
    def month_zhu(self): return self._month_zhu
    @property
    def day_zhu(self): return self._day_zhu
    @property
    def hour_zhu(self): return self._hour_zhu

    def get_zhi_by_index(self, index):
        if 0 <= index < 4:
            return self._zhi_list[index]
        raise IndexError("Invalid index")

