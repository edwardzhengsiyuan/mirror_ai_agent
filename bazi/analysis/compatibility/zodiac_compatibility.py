import sys
import os
from typing import Dict, List, Any

# Ensure the current directory is in the python path
sys.path.append(os.getcwd())

from bazi.core.bazi_chart import BaziChart
from bazi.core import Zhi, Gan

class ZodiacCompatibilityAnalyser:
    """
    分析两个命盘的生肖（年支）合婚关系。
    包含：三合、六合（有利），六冲、六害（不利）。
    """
    
    def __init__(self, chart_a: BaziChart, chart_b: BaziChart):
        self.chart_a = chart_a
        self.chart_b = chart_b
        
        # 获取生肖（年支）
        self.zhi_a = chart_a.year_zhi._zhi
        self.zhi_b = chart_b.year_zhi._zhi
        
        # 生肖名称
        self.name_a = self.zhi_a.chinese_name
        self.name_b = self.zhi_b.chinese_name
        
    def analyse(self) -> Dict[str, Any]:
        result = {
            "shengxiao_a": self.name_a,
            "shengxiao_b": self.name_b,
            "relations": [],
            "score_modifier": 0  # 简单的评分修正建议，正数有利，负数不利
        }
        
        # 1. 检查六合 (有利)
        if self._is_liuhe():
            result["relations"].append(f"六合：{self.name_a}{self.name_b}相合，适宜配婚")
            result["score_modifier"] += 10
            
        # 2. 检查三合 (有利)
        if self._is_sanhe():
            result["relations"].append(f"三合：{self.name_a}{self.name_b}相合，适宜配婚")
            result["score_modifier"] += 5
            
        # 3. 检查六冲 (不利)
        if self._is_liuchong():
            result["relations"].append(f"六冲：{self.name_a}{self.name_b}相冲，不宜配婚")
            result["score_modifier"] -= 10
            
        # 4. 检查六害 (不利)
        if self._is_liuhai():
            result["relations"].append(f"六害：{self.name_a}{self.name_b}相害，不宜配婚")
            result["score_modifier"] -= 5
            
        return result

    def _is_liuhe(self) -> bool:
        """检查地支六合"""
        pairs = [
            {Zhi.ZI, Zhi.CHOU}, {Zhi.YIN, Zhi.HAI},
            {Zhi.MAO, Zhi.XU}, {Zhi.CHEN, Zhi.YOU},
            {Zhi.SI, Zhi.SHEN}, {Zhi.WU, Zhi.WEI}
        ]
        return {self.zhi_a, self.zhi_b} in pairs

    def _is_sanhe(self) -> bool:
        """检查地支三合 (两两组合即算三合局中的半合，这里简化为民间生肖三合说法)
        民間所谓三合生肖，其实是三合局中的任意两个成员通常也被认为有缘，
        虽然严格的三合局需要三个。但在生肖配对中，只要在同一三合局内即算相合。
        """
        groups = [
            {Zhi.SHEN, Zhi.ZI, Zhi.CHEN},
            {Zhi.HAI, Zhi.MAO, Zhi.WEI},
            {Zhi.YIN, Zhi.WU, Zhi.XU},
            {Zhi.SI, Zhi.YOU, Zhi.CHOU}
        ]
        for group in groups:
            if self.zhi_a in group and self.zhi_b in group and self.zhi_a != self.zhi_b:
                return True
        return False

    def _is_liuchong(self) -> bool:
        """检查地支六冲"""
        pairs = [
            {Zhi.ZI, Zhi.WU}, {Zhi.CHOU, Zhi.WEI},
            {Zhi.YIN, Zhi.SHEN}, {Zhi.MAO, Zhi.YOU},
            {Zhi.CHEN, Zhi.XU}, {Zhi.SI, Zhi.HAI}
        ]
        return {self.zhi_a, self.zhi_b} in pairs

    def _is_liuhai(self) -> bool:
        """检查地支六害"""
        pairs = [
            {Zhi.WU, Zhi.CHOU}, {Zhi.ZI, Zhi.WEI},
            {Zhi.SI, Zhi.YIN}, {Zhi.MAO, Zhi.CHEN},
            {Zhi.YOU, Zhi.XU}, {Zhi.HAI, Zhi.SHEN}
        ]
        return {self.zhi_a, self.zhi_b} in pairs
