# Copyright (c) 2025 Siyuan Zheng
#
# All rights reserved.
#
# This software and associated documentation files (the "Software") are the
# proprietary and confidential information of Siyuan Zheng.

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Tuple

from ...analysis.hehua.hehua_analysis import HehuaAnalysis
from ...analysis.power.power_analysis import PowerAnalysis
from ...core import BaziChart, Wuxing
from ...utils.log_helper import LogHelper


@dataclass(frozen=True)
class WuxingVectorPoint:
    x: float
    y: float

    def norm(self) -> float:
        return math.hypot(self.x, self.y)

    def __add__(self, other: "WuxingVectorPoint") -> "WuxingVectorPoint":
        return WuxingVectorPoint(self.x + other.x, self.y + other.y)

    def distance_to(self, other: "WuxingVectorPoint") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


class WuxingVectorCompatibilityAnalyser:
    """
    用五行力量比例构建“正五边形向量空间”并计算：
    - 相似度：两盘终点距离越近越相似（0-100）
    - 互补度：两盘终点向量相加后，距原点越近越互补（0-100）

    说明：
    - 每个五行对应一个单位向量，夹角 72°（360/5）
    - 五行力量用比例（sum=1）作为对应单位向量的系数
    - 终点 = Σ(proportion[wuxing] * unit_vector[wuxing])
    """

    # 约定五行顺序与角度（任意选择起点，只要一致即可）
    _ORDER = [Wuxing.MU, Wuxing.HUO, Wuxing.TU, Wuxing.JIN, Wuxing.SHUI]

    def __init__(self, chart_a: BaziChart, chart_b: BaziChart, enable_debug: bool = False):
        self.chart_a = chart_a
        self.chart_b = chart_b
        self.enable_debug = enable_debug

    def analyse(self) -> Dict[str, Any]:
        a_props = self._calc_wuxing_proportions(self.chart_a)
        b_props = self._calc_wuxing_proportions(self.chart_b)

        a_point = self._to_point(a_props)
        b_point = self._to_point(b_props)

        # 相似度：距离越近越高
        d = a_point.distance_to(b_point)
        d_max = self._max_distance_in_simplex()  # 理论最大距离（两顶点间弦长）
        similarity = self._normalize_inverse_distance(d, d_max)

        # 互补度：向量和越接近原点越高
        s = (a_point + b_point).norm()
        s_max = 2.0  # 单盘终点在单位圆内（<=1），两盘相加最大为2
        complement = self._normalize_inverse_distance(s, s_max)

        res: Dict[str, Any] = {
            "xiangsi_du": similarity,
            "hubu_du": complement,
        }
        if self.enable_debug:
            res["debug"] = {
                "A终点": {"x": a_point.x, "y": a_point.y, "r": a_point.norm()},
                "B终点": {"x": b_point.x, "y": b_point.y, "r": b_point.norm()},
                "AB距离": d,
                "AB距离max": d_max,
                "A+B距离原点": s,
                "A+B距离max": s_max,
                "A五行比例": {wx.chinese_name: float(a_props.get(wx, 0.0)) for wx in Wuxing},
                "B五行比例": {wx.chinese_name: float(b_props.get(wx, 0.0)) for wx in Wuxing},
            }
        return res

    def _calc_wuxing_proportions(self, chart: BaziChart) -> Dict[Wuxing, float]:
        """
        复用现有的合化冲 + 力量分析逻辑，得到五行比例。
        为避免污染外部输出，这里用 enable_terminal_output=False 的 LogHelper。
        """
        log_helper = LogHelper(enable_terminal_output=False)

        # Step 1: HehuaAnalysis
        hehua_analysis = HehuaAnalysis(chart, log_helper)
        _, hehua_results = hehua_analysis.analyse()

        # Step 2: PowerAnalysis 期望 list[list[Force]]
        force_list = []
        for _, forces in hehua_results.items():
            if isinstance(forces, list):
                force_list.extend(forces)
        force_analysis_results = [force_list] if force_list else []

        power_analysis = PowerAnalysis(chart, log_helper, force_analysis_results)
        power_results = power_analysis.analyse()
        return power_results.wuxing_proportions

    def _to_point(self, proportions: Dict[Wuxing, float]) -> WuxingVectorPoint:
        x = 0.0
        y = 0.0
        for idx, wx in enumerate(self._ORDER):
            p = float(proportions.get(wx, 0.0))
            angle = math.radians(72.0 * idx)
            x += p * math.cos(angle)
            y += p * math.sin(angle)
        return WuxingVectorPoint(x, y)

    @staticmethod
    def _max_distance_in_simplex() -> float:
        """
        终点位于正五边形顶点凸包内（单位圆上的五个顶点的凸包）。
        任意两点的最大距离出现在两顶点之间（最大弦长）。
        对五边形，最大角差是 144°（两步），弦长 = 2*sin(72°)。
        """
        return 2.0 * math.sin(math.radians(72.0))

    @staticmethod
    def _normalize_inverse_distance(d: float, d_max: float) -> float:
        if d_max <= 0:
            return 0.0
        score = (1.0 - (d / d_max)) * 100.0
        if score < 0.0:
            return 0.0
        if score > 100.0:
            return 100.0
        return score

