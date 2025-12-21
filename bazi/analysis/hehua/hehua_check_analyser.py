# Copyright (c) 2025 Siyuan Zheng
#
# All rights reserved.
#
# This software and associated documentation files (the "Software") are the
# proprietary and confidential information of Siyuan Zheng.
# Unauthorized copying, modification, distribution, public display, or
# public performance of this software is strictly prohibited.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# analysis/hehua/hehua_check_analyser.py

from itertools import combinations
from typing import Dict, List, Any

from ..base_analyser import BaseAnalyser
from ...core import BaziChart
from ...utils import LogHelper


class HehuaCheckAnalyser(BaseAnalyser):
    def __init__(self, bazi_chart: BaziChart, log_helper: LogHelper):
        super().__init__(bazi_chart, log_helper)
        self._gan_list = self._bazi_chart.gan_list
        self._zhi_list = self._bazi_chart.zhi_list

    def analyse(self) -> Dict[str, List[Any]]:
        # 获取天干和地支的中文名称列表
        gan_names = [gan._chinese_name for gan in self._gan_list]
        zhi_names = [zhi._chinese_name for zhi in self._zhi_list]

        # 调用各个检查方法
        tian_gan_wu_he_results, tian_gan_wu_he_name_combs = self.check_tian_gan_wu_he(gan_names)
        tian_gan_xiang_chong_results, tian_gan_xiang_chong_name_combs = self.check_tian_gan_xiang_chong(gan_names)
        di_zhi_san_hui_results, di_zhi_san_hui_name_combs = self.check_di_zhi_san_hui(zhi_names)
        di_zhi_san_he_results, di_zhi_san_he_name_combs = self.check_di_zhi_san_he(zhi_names)
        di_zhi_ban_he_results, di_zhi_ban_he_name_combs = self.check_di_zhi_ban_he(zhi_names, di_zhi_san_he_results)
        di_zhi_liu_he_results, di_zhi_liu_he_name_combs = self.check_di_zhi_liu_he(zhi_names)
        di_zhi_liu_chong_results, di_zhi_liu_chong_name_combs = self.check_di_zhi_liu_chong(zhi_names)

        # 组装结果
        result = {
            "天干五合": tian_gan_wu_he_results,
            "天干相冲": tian_gan_xiang_chong_results,
            "地支三会": di_zhi_san_hui_results,
            "地支三合": di_zhi_san_he_results,
            "地支半合": di_zhi_ban_he_results,
            "地支六合": di_zhi_liu_he_results,
            "地支六冲": di_zhi_liu_chong_results
        }

        # 生成日志输出
        tian_gan_wu_he_word = "天干五合：" + "，".join(tian_gan_wu_he_name_combs) if len(tian_gan_wu_he_results) > 0 else ""
        tian_gan_xiang_chong_word = "天干相冲：" + "，".join(tian_gan_xiang_chong_name_combs) if len(tian_gan_xiang_chong_results) > 0 else ""
        di_zhi_san_hui_word = "地支三会：" + "，".join(di_zhi_san_hui_name_combs) if len(di_zhi_san_hui_results) > 0 else ""
        di_zhi_san_he_word = "地支三合：" + "，".join(di_zhi_san_he_name_combs) if len(di_zhi_san_he_results) > 0 else ""
        di_zhi_ban_he_word = "地支半合：" + "，".join(di_zhi_ban_he_name_combs) if len(di_zhi_ban_he_results) > 0 else ""
        di_zhi_liu_he_word = "地支六合：" + "，".join(di_zhi_liu_he_name_combs) if len(di_zhi_liu_he_results) > 0 else ""
        di_zhi_liu_chong_word = "地支六冲：" + "，".join(di_zhi_liu_chong_name_combs) if len(di_zhi_liu_chong_results) > 0 else ""
        word_list = []
        word = "\n【天干地支合化冲分析】：\n"
        for word_item in [tian_gan_wu_he_word, tian_gan_xiang_chong_word, di_zhi_san_hui_word, di_zhi_san_he_word, di_zhi_ban_he_word, di_zhi_liu_he_word, di_zhi_liu_chong_word]:
            if len(word_item) > 0:
                word_list.append(word_item)
        if len(word_list) > 0:
            word += "可能存在的天干地支合化冲情形初步判断如下：\n" + '；\n'.join(word_list) + "。\n"
        else:
            word += "暂未发现原局存在的天干地支合化冲。\n"
        self._log_helper.info(word)

        # 返回检查结果
        return result

    def check_combinations(self, target_combinations, names):
        results = []
        indices_list = list(range(len(names)))
        for combination in target_combinations:
            for indices in combinations(indices_list, len(combination)):
                if set(combination) == set(names[index] for index in indices):
                    results.append(list(indices))
        return results

    def check_di_zhi_san_hui(self, zhi_names):
        di_zhi_san_hui_combinations = [
            {"寅", "卯", "辰"},
            {"巳", "午", "未"},
            {"申", "酉", "戌"},
            {"亥", "子", "丑"}
        ]
        results = self.check_combinations(di_zhi_san_hui_combinations, zhi_names)
        name_combs = [self.get_name_by_index(zhi_names, indices) + '三会' for indices in results]
        return results, name_combs

    def check_di_zhi_san_he(self, zhi_names):
        di_zhi_san_he_combinations = [
            {"寅", "午", "戌"},
            {"巳", "酉", "丑"},
            {"申", "子", "辰"},
            {"亥", "卯", "未"}
        ]
        results = self.check_combinations(di_zhi_san_he_combinations, zhi_names)
        name_combs = [self.get_name_by_index(zhi_names, indices) + '三合'  for indices in results]
        return results, name_combs

    def check_di_zhi_ban_he(self, zhi_names, di_zhi_san_he_results):
        di_zhi_ban_he_combinations = [
            {"寅", "午"}, {"午", "戌"},
            {"巳", "酉"}, {"酉", "丑"},
            {"申", "子"}, {"子", "辰"},
            {"亥", "卯"}, {"卯", "未"}
        ]
        results = []
        for combination in di_zhi_ban_he_combinations:
            corresponding_di_zhi_san_he_combination = None
            if combination == {"寅", "午"} or combination == {"午", "戌"}:
                corresponding_di_zhi_san_he_combination = {"寅", "午", "戌"}
            elif combination == {"巳", "酉"} or combination == {"酉", "丑"}:
                corresponding_di_zhi_san_he_combination = {"巳", "酉", "丑"}
            elif combination == {"申", "子"} or combination == {"子", "辰"}:
                corresponding_di_zhi_san_he_combination = {"申", "子", "辰"}
            elif combination == {"亥", "卯"} or combination == {"卯", "未"}:
                corresponding_di_zhi_san_he_combination = {"亥", "卯", "未"}
            
            if corresponding_di_zhi_san_he_combination and corresponding_di_zhi_san_he_combination in [{zhi_names[i] for i in indices} for indices in di_zhi_san_he_results]:
                continue
            
            sorted_combination = sorted(combination)
            if sorted_combination == sorted([name for name in zhi_names if name in combination]):
                indices = [i for i, name in enumerate(zhi_names) if name in combination]
                results.append(indices)
        name_combs = [self.get_name_by_index(zhi_names, indices) + '半合' for indices in results]
        return results, name_combs

    def check_di_zhi_liu_he(self, zhi_names):
        di_zhi_liu_he_combinations = [
            {"子", "丑"}, {"寅", "亥"},
            {"卯", "戌"}, {"辰", "酉"},
            {"巳", "申"}, {"午", "未"}
        ]
        results = self.check_combinations(di_zhi_liu_he_combinations, zhi_names)
        
        # 处理特殊情况
        di_zhi_san_hui_combinations = [
            {"亥", "子", "丑"},
            {"巳", "午", "未"}
        ]
        
        filtered_results = []
        for result in results:
            # 获取当前六合组合对应的地支
            combination = {zhi_names[i] for i in result}
            if combination == {"子", "丑"}:
                # 检查是否存在亥子丑三会组合
                if {"亥", "子", "丑"} not in [set(zhi_names[i] for i in indices) for indices in self.check_combinations(di_zhi_san_hui_combinations, zhi_names)]:
                    filtered_results.append(result)
            elif combination == {"午", "未"}:
                # 检查是否存在巳午未三会组合
                if {"巳", "午", "未"} not in [set(zhi_names[i] for i in indices) for indices in self.check_combinations(di_zhi_san_hui_combinations, zhi_names)]:
                    filtered_results.append(result)
            else:
                filtered_results.append(result)

        name_combs = [self.get_name_by_index(zhi_names, indices) + '六合' for indices in filtered_results]
        return filtered_results, name_combs

    def check_di_zhi_liu_chong(self, zhi_names):
        di_zhi_liu_chong_combinations = [
            {"子", "午"}, {"寅", "申"},
            {"卯", "酉"}, {"辰", "戌"},
            {"巳", "亥"}, {"丑", "未"}
        ]
        results = self.check_combinations(di_zhi_liu_chong_combinations, zhi_names)
        name_combs = [self.get_name_by_index(zhi_names, indices) + '六冲' for indices in results]
        return results, name_combs

    def check_tian_gan_wu_he(self, gan_names):
        tian_gan_wu_he_combinations = [
            {"甲", "己"}, {"乙", "庚"},
            {"丙", "辛"}, {"丁", "壬"},
            {"戊", "癸"}
        ]
        results = self.check_combinations(tian_gan_wu_he_combinations, gan_names)
        name_combs = [self.get_name_by_index(gan_names, indices) + '五合' for indices in results]
        return results, name_combs

    def check_tian_gan_xiang_chong(self, gan_names):
        tian_gan_xiang_chong_combinations = [
            {"甲", "庚"}, {"乙", "辛"},
            {"丙", "壬"}, {"丁", "癸"},
            {"戊", "子"}  # 注意这里可能需要根据实际情况调整
        ]
        results = self.check_combinations(tian_gan_xiang_chong_combinations, gan_names)
        name_combs = [self.get_name_by_index(gan_names, indices) + '相冲' for indices in results]
        return results, name_combs

    def get_name_by_index(self, names, indices):
        return ''.join([names[i] for i in indices])

