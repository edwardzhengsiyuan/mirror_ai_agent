from typing import Dict, Any

from ..base_analyser import BaseAnalyser
from ...core.bazi_chart import BaziChart
from ...utils import LogHelper


class XinghaiAnalyser(BaseAnalyser):
    def __init__(self, bazi_chart: BaziChart, log_helper: LogHelper):
        super().__init__(bazi_chart, log_helper)
        self.without_time = self._bazi_chart.without_time
        self.wu_en_zhi_xing_combinations = [{"寅", "巳", "申"}]
        self.shi_shi_zhi_xing_combinations = [{"丑", "戌", "未"}]
        self.wu_li_zhi_xing_combinations = [{"子", "卯"}]
        self.xiang_hai_combinations = [
            {"子", "未"}, {"丑", "午"}, {"寅", "巳"}, {"卯", "辰"},
            {"申", "亥"}, {"酉", "戌"}
        ]

    def check_combinations(self, combinations, zhi_names):
        results = {}
        zhi_set = set(zhi_names)
        for combination in combinations:
            if combination.issubset(zhi_set):
                indices = tuple(i for i, name in enumerate(zhi_names) if name in combination)
                results[tuple(combination)] = indices
        return results

    def check_san_xing(self, zhi_names):
        results = {}
        zhi_set = set(zhi_names)
        if {"寅", "巳", "申"}.issubset(zhi_set) and "亥" not in zhi_set:
            indices = tuple(i for i, name in enumerate(zhi_names) if name in {"寅", "巳", "申"})
            results[("寅", "巳", "申")] = indices

        if {"丑", "戌", "未"}.issubset(zhi_set) and "辰" not in zhi_set:
            indices = tuple(i for i, name in enumerate(zhi_names) if name in {"丑", "戌", "未"})
            results[("丑", "戌", "未")] = indices
        return results

    def check_zi_xing(self, zhi_names):
        results = {}
        zhi_count = {zhi: zhi_names.count(zhi) for zhi in set(zhi_names)}
        for zhi in ["辰", "午", "酉", "亥"]:
            if zhi_count.get(zhi, 0) > 1:
                indices = tuple(i for i, name in enumerate(zhi_names) if name == zhi)
                results[(zhi,)] = indices
        return results

    def analyse(self) -> Dict[str, Any]:
        if (self.without_time):
            zhi_list = [
                self._bazi_chart.year_zhi,
                self._bazi_chart.month_zhi,
                self._bazi_chart.day_zhi
            ]
        else:
            zhi_list = [
                self._bazi_chart.year_zhi,
                self._bazi_chart.month_zhi,
                self._bazi_chart.day_zhi,
                self._bazi_chart.hour_zhi
            ]

        zhi_names = [zhi._chinese_name for zhi in zhi_list]

        results_xing = {}
        results_hai = {}
        results_xing.update(self.check_san_xing(zhi_names))
        results_xing.update(self.check_combinations(self.wu_li_zhi_xing_combinations, zhi_names))
        results_xing.update(self.check_zi_xing(zhi_names))
        results_hai.update(self.check_combinations(self.xiang_hai_combinations, zhi_names))

        res = {"刑": results_xing, "穿": results_hai}

        # 记录分析结果到日志
        self._log_results(res)

        return res

    def _log_results(self, res: Dict[str, Any]) -> None:
        """将分析结果记录到日志中"""
        self._log_helper.info("【地支刑穿分析】\n")
        for key, value in res.items():
            if value:
                if (self.without_time):
                    zhu_names = ['年支', '月支', '日支']
                else:
                    zhu_names = ['年支', '月支', '日支', '时支']
                for combination, indices in value.items():
                    involved_zhu = [zhu_names[i] for i in indices]
                    zhi_names_list = [x._chinese_name for x in [self._bazi_chart.zhi_list[i] for i in indices]]
                    message = f"地支{key}：{f'{str(key)}'.join([x + y for x, y in zip(involved_zhu, zhi_names_list)])}。\n"
                    self._log_helper.info(message)
            else:
                self._log_helper.info(f"原局地支无{key}。\n")
