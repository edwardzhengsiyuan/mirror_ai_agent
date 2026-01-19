# Copyright (c) 2025 Siyuan Zheng
#
# All rights reserved.
#
# This software and associated documentation files (the "Software") are the
# proprietary and confidential information of Siyuan Zheng.

import math
from typing import Dict, Any, Tuple
from ...core import Wuxing

class WuxingCompatibilityAnalyser:
    """
    五行力量相似度与互补度分析器
    
    原理：
    将五行（木、火、土、金、水）映射到二维平面上的 5 个向量，间隔 72 度。
    每个命盘的五行力量比例作为各方向向量的长度，计算矢量和，得到“五行合力点”。
    
    1. 相似度 (Similarity):
       计算两个命盘合力点之间的欧氏距离。距离越近，相似度越高。
       Score = (1 - Distance / MaxDistance) * 100
       
    2. 互补度 (Complementarity):
       计算两个命盘合力向量叠加后的模长（即合成向量距离原点的距离）。
       叠加后越接近原点（模长越小），说明五行越平衡，互补度越高。
       Score = (1 - CombinedMagnitude / MaxCombinedMagnitude) * 100
    """
    
    def __init__(self):
        # 定义五行对应的角度 (弧度)
        # 木 -> 火 -> 土 -> 金 -> 水 (顺时针或逆时针均可，这里按相生顺序)
        # 0, 72, 144, 216, 288 度
        self.angles = {
            Wuxing.MU: 0.0,
            Wuxing.HUO: 72.0 * math.pi / 180.0,
            Wuxing.TU: 144.0 * math.pi / 180.0,
            Wuxing.JIN: 216.0 * math.pi / 180.0,
            Wuxing.SHUI: 288.0 * math.pi / 180.0,
        }
        # 归一化参数估计
        # 单个盘合力向量最大模长约为 1 (单五行 100%)
        # 两个盘合力向量距离最大值约为 2 (反向)
        self.MAX_DISTANCE = 2.0
        # 两个盘向量相加最大模长约为 2 (同向)
        self.MAX_COMBINED_MAGNITUDE = 2.0

    def analyse(self, chart_a_props: Dict[Wuxing, float], chart_b_props: Dict[Wuxing, float]) -> Dict[str, Any]:
        """
        Args:
            chart_a_props: Chart A 的五行比例字典 {Wuxing.MU: 0.2, ...}
            chart_b_props: Chart B 的五行比例字典
            
        Returns:
            Dict: {
                "similarity_score": float (0-100),
                "complementarity_score": float (0-100),
                "vector_a": (x, y),
                "vector_b": (x, y)
            }
        """
        vec_a = self._calculate_vector(chart_a_props)
        vec_b = self._calculate_vector(chart_b_props)
        
        # 1. 相似度计算 (距离越小越好)
        dist = math.sqrt((vec_a[0] - vec_b[0])**2 + (vec_a[1] - vec_b[1])**2)
        similarity_score = max(0, min(100, (1 - dist / self.MAX_DISTANCE) * 100))
        
        # 2. 互补度计算 (向量和的模长越小越好)
        combined_vec = (vec_a[0] + vec_b[0], vec_a[1] + vec_b[1])
        combined_mag = math.sqrt(combined_vec[0]**2 + combined_vec[1]**2)
        complementarity_score = max(0, min(100, (1 - combined_mag / self.MAX_COMBINED_MAGNITUDE) * 100))
        
        return {
            "similarity_score": round(similarity_score, 2),
            "complementarity_score": round(complementarity_score, 2),
            # "debug_vector_a": vec_a,
            # "debug_vector_b": vec_b,
            # "debug_dist": dist,
            # "debug_combined_mag": combined_mag
        }

    def _calculate_vector(self, props: Dict[Wuxing, float]) -> Tuple[float, float]:
        x, y = 0.0, 0.0
        for wuxing, angle in self.angles.items():
            proportion = props.get(wuxing, 0.0)
            x += proportion * math.cos(angle)
            y += proportion * math.sin(angle)
        return x, y
