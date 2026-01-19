# Copyright (c) 2025 Siyuan Zheng
#
# All rights reserved.
#
# This software and associated documentation files (the "Software") are the
# proprietary and confidential information of Siyuan Zheng.

from typing import Any, Dict

from ...core import Zhi, BaziChart
from ...core.property import (
    Shengxiao,
    ZodiacCompatibilityDetail,
    ZodiacCompatibilityFavorability,
    ZodiacCompatibilityRelation,
)


class ZodiacCompatibilityAnalyser:
    """
    生肖合婚（民间简化版）：
    - 以双方年支（生肖）为准
    - 六合、三合：有利姻缘
    - 六冲、六害：不利配婚
    """

    def __init__(self, chart_a: BaziChart, chart_b: BaziChart):
        self.chart_a = chart_a
        self.chart_b = chart_b

    def analyse(self) -> Dict[str, Any]:
        a_year_zhi = self.chart_a.year_zhi.get()
        b_year_zhi = self.chart_b.year_zhi.get()

        a_shengxiao = self._get_shengxiao_enum(a_year_zhi)
        b_shengxiao = self._get_shengxiao_enum(b_year_zhi)

        liuhe_pairs = {
            frozenset([Zhi.ZI, Zhi.CHOU]),
            frozenset([Zhi.YIN, Zhi.HAI]),
            frozenset([Zhi.MAO, Zhi.XU]),
            frozenset([Zhi.CHEN, Zhi.YOU]),
            frozenset([Zhi.SI, Zhi.SHEN]),
            frozenset([Zhi.WU, Zhi.WEI]),
        }
        sanhe_groups = [
            {Zhi.SHEN, Zhi.ZI, Zhi.CHEN},  # 申子辰
            {Zhi.HAI, Zhi.MAO, Zhi.WEI},  # 亥卯未
            {Zhi.YIN, Zhi.WU, Zhi.XU},  # 寅午戌
            {Zhi.SI, Zhi.YOU, Zhi.CHOU},  # 巳酉丑
        ]
        liuhai_pairs = {
            frozenset([Zhi.WU, Zhi.CHOU]),  # 午丑害
            frozenset([Zhi.ZI, Zhi.WEI]),  # 子未害
            frozenset([Zhi.SI, Zhi.YIN]),  # 巳寅害
            frozenset([Zhi.MAO, Zhi.CHEN]),  # 卯辰害
            frozenset([Zhi.YOU, Zhi.XU]),  # 酉戌害
            frozenset([Zhi.HAI, Zhi.SHEN]),  # 亥申害
        }
        liuchong_pairs = {
            frozenset([Zhi.ZI, Zhi.WU]),  # 子午冲
            frozenset([Zhi.CHOU, Zhi.WEI]),  # 丑未冲
            frozenset([Zhi.YIN, Zhi.SHEN]),  # 寅申冲
            frozenset([Zhi.MAO, Zhi.YOU]),  # 卯酉冲
            frozenset([Zhi.CHEN, Zhi.XU]),  # 辰戌冲
            frozenset([Zhi.SI, Zhi.HAI]),  # 巳亥冲
        }

        pair = frozenset([a_year_zhi, b_year_zhi])
        relation, favorable, detail = self._judge_relation(
            a_year_zhi=a_year_zhi,
            b_year_zhi=b_year_zhi,
            pair=pair,
            liuhe_pairs=liuhe_pairs,
            sanhe_groups=sanhe_groups,
            liuchong_pairs=liuchong_pairs,
            liuhai_pairs=liuhai_pairs,
        )

        return {
            "a_shengxiao": a_shengxiao.value,
            "b_shengxiao": b_shengxiao.value,
            "a_nianzhi": a_year_zhi.name,
            "b_nianzhi": b_year_zhi.name,
            "relation": relation.value,
            "favorable": favorable.value,
            "detail": detail.value,
        }

    @staticmethod
    def _judge_relation(
        *,
        a_year_zhi: Zhi,
        b_year_zhi: Zhi,
        pair: frozenset,
        liuhe_pairs: set,
        sanhe_groups: list,
        liuchong_pairs: set,
        liuhai_pairs: set,
    ) -> tuple[ZodiacCompatibilityRelation, ZodiacCompatibilityFavorability, ZodiacCompatibilityDetail]:
        if a_year_zhi == b_year_zhi:
            return (
                ZodiacCompatibilityRelation.SAME,
                ZodiacCompatibilityFavorability.NEUTRAL,
                ZodiacCompatibilityDetail.SAME,
            )

        if pair in liuhe_pairs:
            return (
                ZodiacCompatibilityRelation.LIUHE,
                ZodiacCompatibilityFavorability.FAVORABLE,
                ZodiacCompatibilityDetail.LIUHE,
            )

        if any(a_year_zhi in g and b_year_zhi in g for g in sanhe_groups):
            return (
                ZodiacCompatibilityRelation.SANHE,
                ZodiacCompatibilityFavorability.FAVORABLE,
                ZodiacCompatibilityDetail.SANHE,
            )

        if pair in liuchong_pairs:
            return (
                ZodiacCompatibilityRelation.LIUCHONG,
                ZodiacCompatibilityFavorability.UNFAVORABLE,
                ZodiacCompatibilityDetail.LIUCHONG,
            )

        if pair in liuhai_pairs:
            return (
                ZodiacCompatibilityRelation.LIUHAI,
                ZodiacCompatibilityFavorability.UNFAVORABLE,
                ZodiacCompatibilityDetail.LIUHAI,
            )

        return (
            ZodiacCompatibilityRelation.NEUTRAL,
            ZodiacCompatibilityFavorability.NEUTRAL,
            ZodiacCompatibilityDetail.NEUTRAL,
        )

    @staticmethod
    def _get_shengxiao_enum(zhi: Zhi) -> Shengxiao:
        mapping = {
            Zhi.ZI: Shengxiao.SHU,
            Zhi.CHOU: Shengxiao.NIU,
            Zhi.YIN: Shengxiao.HU,
            Zhi.MAO: Shengxiao.TU,
            Zhi.CHEN: Shengxiao.LONG,
            Zhi.SI: Shengxiao.SHE,
            Zhi.WU: Shengxiao.MA,
            Zhi.WEI: Shengxiao.YANG,
            Zhi.SHEN: Shengxiao.HOU,
            Zhi.YOU: Shengxiao.JI,
            Zhi.XU: Shengxiao.GOU,
            Zhi.HAI: Shengxiao.ZHU,
        }
        return mapping[zhi]

