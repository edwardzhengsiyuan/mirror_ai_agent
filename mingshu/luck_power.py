"""Recalculate five-element power after appending a luck-cycle pillar."""

from __future__ import annotations

from typing import Any

from bazi.analysis.hehua.hehua_analysis import HehuaAnalysis
from bazi.analysis.power.bazi_power_chart import BaziPowerChart
from bazi.analysis.power.power_transformer import PowerTransformer
from bazi.core import Gan, Wuxing, Zhi
from bazi.core.bazi_chart import BaziChartGan, BaziChartZhi, Zhu
from bazi.utils import LogHelper


ELEMENT_ORDER = ("木", "火", "土", "金", "水")


def _label(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("name_label") or value.get("label") or "")
    return str(value or "")


class LuckAugmentedChart:
    """A natal chart with one extra pillar used only for power analysis."""

    def __init__(self, facts: dict, cycle: dict):
        pillars = list((facts.get("chart") or {}).get("pillars") or [])
        if len(pillars) not in {3, 4}:
            raise ValueError("luck power analysis requires three or four natal pillars")

        day_master = _label((facts.get("chart") or {}).get("day_master"))
        if not day_master:
            day_master = _label((pillars[2].get("gan") or {}))
        day_gan = Gan.from_chinese(day_master)

        gan_values = [Gan.from_chinese(_label(item.get("gan"))) for item in pillars]
        zhi_values = [Zhi.from_chinese(_label(item.get("zhi"))) for item in pillars]
        gan_values.append(Gan.from_chinese(_label(cycle.get("gan"))))
        zhi_values.append(Zhi.from_chinese(_label(cycle.get("zhi"))))

        self.without_time = len(pillars) == 3
        self.pillar_names = (
            ["年", "月", "日", "运"]
            if self.without_time
            else ["年", "月", "日", "时", "运"]
        )
        self._gan_list = [
            BaziChartGan(value, day_gan, index)
            for index, value in enumerate(gan_values)
        ]
        self._zhi_list = [
            BaziChartZhi(value, day_gan, index)
            for index, value in enumerate(zhi_values)
        ]
        self._zhu_list = [
            Zhu(gan, zhi)
            for gan, zhi in zip(self._gan_list, self._zhi_list)
        ]

        self._year_gan, self._month_gan, self._day_gan = self._gan_list[:3]
        self._year_zhi, self._month_zhi, self._day_zhi = self._zhi_list[:3]
        if not self.without_time:
            self._hour_gan = self._gan_list[3]
            self._hour_zhi = self._zhi_list[3]

    @property
    def gan_list(self):
        return self._gan_list

    @property
    def zhi_list(self):
        return self._zhi_list

    @property
    def zhu_list(self):
        return self._zhu_list

    @property
    def year_gan(self):
        return self._year_gan

    @property
    def year_zhi(self):
        return self._year_zhi

    @property
    def month_gan(self):
        return self._month_gan

    @property
    def month_zhi(self):
        return self._month_zhi

    @property
    def day_gan(self):
        return self._day_gan

    @property
    def day_zhi(self):
        return self._day_zhi

    @property
    def hour_gan(self):
        return None if self.without_time else self._hour_gan

    @property
    def hour_zhi(self):
        return None if self.without_time else self._hour_zhi

    def get_zhi_by_index(self, index: int):
        return self._zhi_list[index]


def calculate_luck_wuxing_power(facts: dict, cycle: dict) -> dict:
    """Return augmented proportions and deltas against the natal chart."""

    baseline_items = list((facts.get("analysis_facts") or {}).get("wuxing") or [])
    baseline = {
        str(item.get("label") or ""): float(item.get("percent") or 0.0)
        for item in baseline_items
    }
    if set(baseline) != set(ELEMENT_ORDER):
        raise ValueError("natal five-element proportions are incomplete")

    chart = LuckAugmentedChart(facts, cycle)
    log_helper = LogHelper(
        name=f"mingshu_luck_power_{cycle.get('id') or cycle.get('name')}",
        enable_terminal_output=False,
    )
    _, forces = HehuaAnalysis(chart, log_helper).analyse()
    power_chart = BaziPowerChart(chart, forces)
    transformed = PowerTransformer(chart, power_chart, forces, log_helper).transform()
    transformed.calculate_powers()

    adjusted = {
        wuxing.chinese_name: round(
            float(transformed.wuxing_proportions.get(wuxing, 0.0)) * 100.0,
            2,
        )
        for wuxing in Wuxing
    }
    series = [
        {
            "name": name,
            "baseline": round(baseline[name], 2),
            "adjusted": adjusted[name],
            "delta": round(adjusted[name] - baseline[name], 2),
        }
        for name in ELEMENT_ORDER
    ]
    rising = sorted(series, key=lambda item: item["delta"], reverse=True)
    falling = sorted(series, key=lambda item: item["delta"])
    return {
        "series": series,
        "largest_rise": rising[0],
        "largest_fall": falling[0],
        "method": (
            "在原局四柱后加入本步大运干支，沿用原脚本的月令、藏干、"
            "透干通根、生克与合化力量流程重新计算；差值为相对原局的百分点变化。"
        ),
    }
