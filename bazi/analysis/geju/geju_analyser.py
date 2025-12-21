from typing import List, Any

from ..base_analyser import BaseAnalyser
from ..hehua import (
    DiZhiSanHui,
    DiZhiSanHe
)
from ...core import Shishen, Wuxing
from ...core.bazi_chart import BaziChart
from ...utils import LogHelper


class GejuAnalyser(BaseAnalyser):
    def __init__(self, bazi_chart: BaziChart, log_helper: LogHelper, hehua_analysis_results, shensha_results):
        super().__init__(bazi_chart, log_helper)
        self.without_time = self._bazi_chart.without_time
        self._hehua_analysis_results: Any = hehua_analysis_results  # 根据实际类型替换 Any
        self._shensha_results: Any = shensha_results  # 根据实际类型替换 Any
        self._geju: List[str] = []

    def analyse(self) -> List[str]:
        # 获取月支的五行
        month_zhi_wuxing = self._bazi_chart.month_zhi._zhi.wuxing
        day_gan_wuxing = self._bazi_chart.day_gan._gan.wuxing

        # 步骤1: 如果月支的五行与日主的五行不同
        if month_zhi_wuxing != day_gan_wuxing:
            self._analyse_different_wuxing(month_zhi_wuxing, day_gan_wuxing)
        else:
            self._analyse_same_wuxing(month_zhi_wuxing, day_gan_wuxing)

        # 处理格局冲突
        if self._geju:
            self._resolve_conflicting_geju()

        # 记录日志
        self._log_results()

        return self._geju

    def _analyse_different_wuxing(self, month_zhi_wuxing: Wuxing, day_gan_wuxing: Wuxing) -> None:
        # a. 检查月支第一个藏干是否透出
        first_hidden_gan = self._bazi_chart.month_zhi._hidden_gans[0]
        if self.is_touchu(first_hidden_gan):
            shishen = self._bazi_chart.calculate_shishen(self._bazi_chart.day_gan, first_hidden_gan)
            self._geju.append(shishen.chinese_name + "格")

        # b. 检查月支其他藏干是否透出
        for hidden_gan in self._bazi_chart.month_zhi._hidden_gans[1:]:
            if self.is_touchu(hidden_gan):
                shishen = self._bazi_chart.calculate_shishen(self._bazi_chart.day_gan, hidden_gan)
                self._geju.append(shishen.chinese_name + "格")


        # c. 检查地支中是否有三合，三会存在
        self.check_sanhe_sanhui()

        # d. 检查月干是否同根于年支日支时支
        if self.is_tonggen(self._bazi_chart.month_gan):
            shishen = self._bazi_chart.calculate_shishen(self._bazi_chart.day_gan, self._bazi_chart.month_gan)
            self._geju.append(shishen.chinese_name + "格")

        # e. 检查年柱时柱是否有地支藏干透出同柱的天干
        if self.without_time:
            temp_zhu_list = [self._bazi_chart.year_zhu]
        else:
            temp_zhu_list = [self._bazi_chart.year_zhu, self._bazi_chart.hour_zhu]
        for zhu in temp_zhu_list:
            for hidden_gan in zhu.zhi._hidden_gans:
                if hidden_gan == zhu.gan:
                    shishen = self._bazi_chart.calculate_shishen(self._bazi_chart.day_gan, hidden_gan)
                    self._geju.append(shishen.chinese_name + "格")

        # f. 检查年柱日柱时柱是否有地支透出到其它位置的天干
        if self.without_time:
            temp_zhu_list = [self._bazi_chart.year_zhu, self._bazi_chart.day_zhu]
        else:
            temp_zhu_list = [self._bazi_chart.year_zhu, self._bazi_chart.day_zhu, self._bazi_chart.hour_zhu]
        for zhu in temp_zhu_list:
            for hidden_gan in zhu.zhi._hidden_gans:
                if self.is_touchu(hidden_gan, exclude_zhu=zhu):
                    shishen = self._bazi_chart.calculate_shishen(self._bazi_chart.day_gan, hidden_gan)
                    self._geju.append(shishen.chinese_name + "格")

    def _analyse_same_wuxing(self, month_zhi_wuxing: Wuxing, day_gan_wuxing: Wuxing) -> None:
        # a. 检查地支中是否有三合，三会存在
        self.check_sanhe_sanhui()

        # b. 检查月令是否为日主的羊刃或禄神
        for shensha in self._shensha_results:
            if shensha['name'] in ['Yangren', 'Lushen'] and shensha['position'] == self._bazi_chart.month_zhu:
                self._geju.append(shensha['chinese_name'] + "格")

        # d. 检查月干是否同根于年支日支时支
        if self.is_tonggen(self._bazi_chart.month_gan):
            shishen = self._bazi_chart.calculate_shishen(self._bazi_chart.day_gan, self._bazi_chart.month_gan)
            self._geju.append(shishen.chinese_name + "格")

        # e. 检查年柱时柱是否有地支藏干透出同柱的天干
        if self.without_time:
            temp_zhu_list = [self._bazi_chart.year_zhu]
        else:
            temp_zhu_list = [self._bazi_chart.year_zhu, self._bazi_chart.hour_zhu]
        for zhu in temp_zhu_list:
            for hidden_gan in zhu.zhi._hidden_gans:
                if hidden_gan == zhu.gan:
                    shishen = self._bazi_chart.calculate_shishen(self._bazi_chart.day_gan, hidden_gan)
                    self._geju.append(shishen.chinese_name + "格")

        # f. 检查年柱日柱时柱是否有地支透出到其它位置的天干
        if self.without_time:
            temp_zhu_list = [self._bazi_chart.year_zhu, self._bazi_chart.day_zhu]
        else:
            temp_zhu_list = [self._bazi_chart.year_zhu, self._bazi_chart.day_zhu, self._bazi_chart.hour_zhu]
        for zhu in temp_zhu_list:
            for hidden_gan in zhu.zhi._hidden_gans:
                if self.is_touchu(hidden_gan, exclude_zhu=zhu):
                    shishen = self._bazi_chart.calculate_shishen(self._bazi_chart.day_gan, hidden_gan)
                    self._geju.append(shishen.chinese_name + "格")

    def is_touchu(self, hidden_gan, exclude_zhu=None):
        for zhu in self._bazi_chart.zhu_list:
            if exclude_zhu and zhu == exclude_zhu:
                continue
            if zhu.gan == hidden_gan:
                return True
        return False

    def is_tonggen(self, gan):
        for zhi in self._bazi_chart.zhi_list:
            if gan in zhi._hidden_gans:
                return True
        return False

    def check_sanhe_sanhui(self):
        for force in self._hehua_analysis_results:
            if isinstance(force, DiZhiSanHe) or isinstance(force, DiZhiSanHui):
                center_zhi = self.get_center_zhi(force.element_index)
                if center_zhi:
                    shishen = self._bazi_chart.calculate_shishen(self._bazi_chart.day_gan, center_zhi)
                    if shishen not in [Shishen.BIJIAN, Shishen.JIECAI]:
                        geju_name = self.resolve_hehui_geju(shishen.chinese_name)
                        self._geju.append(geju_name + "格")
                    else:
                        self._geju.append("专旺格")

    def get_center_zhi(self, indices):
        if len(indices) == 3:
            return self._bazi_chart.zhi_list[indices[1]]
        return None

    def _resolve_conflicting_geju(self) -> None:
        unique_geju = list(set(self._geju))
        unique_geju.sort(key=self._geju.index)
        conflicts = [
            ('食神格', '伤官格'),
            ('正官格', '七杀格'),
            ('正财格', '偏财格'),
            ('正印格', '偏印格')
        ]
        for ge1, ge2 in conflicts:
            if ge1 in unique_geju and ge2 in unique_geju:
                unique_geju.remove(ge1)
        self._geju = unique_geju

    def resolve_hehui_geju(self, shishen_name):
        mapping = {
            '食神': '伤官',
            '正官': '七杀',
            '正财': '偏财',
            '正印': '偏印'
        }
        return mapping.get(shishen_name, shishen_name)

    def _log_results(self) -> None:
        self._log_helper.info("【格局分析】：\n")
        if len(self._geju) == 1:
            self._log_helper.info(f"格局：{self._geju[0]}。\n")
        elif len(self._geju) > 1:
            self._log_helper.info(f"格局：{'，带'.join(self._geju)}。\n")
        else:
            self._log_helper.info("没有符合的格局。\n")