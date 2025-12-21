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

# analysis/power/power_transformer.py

import copy
from collections import Counter

from ..hehua import (
    TianGanHe,
    TianGanChong,
    DiZhiSanHui,
    DiZhiSanHe,
    DiZhiBanHe,
    DiZhiLiuHe,
    DiZhiLiuChong
)
from ...core import Wuxing, Gan, Zhi

# 定义全局变量
MONTH_FORCE = 0.3
TIANTOUDICANG_FORCE = 0.2
SANHUI_FORCE = 2
SANHE_FORCE = 1.5
SHENGKE_FORCE = 0.02

zhu_name = ['年', '月', '日', '时']

def calculate_force(element, wuxing, distance):
    Ma = element.M
    base_force = element.wuxing_power[wuxing] * Ma
    decay_factor = max(1 - 0.2 * distance, 0)
    force = base_force * decay_factor
    return force

def manhattan_distance(pos1, pos2):
    x1, y1 = pos1
    x2, y2 = pos2
    return abs(x1 - x2) + abs(y1 - y2)

class PowerTransformer:
    def __init__(self, bazi_chart, bazi_power_chart, force_analysis_results, log_helper):
        self.bazi_chart = bazi_chart
        self.bazi_power_chart = bazi_power_chart
        self.force_analysis_results = force_analysis_results
        self.log_helper = log_helper

    def apply_hehuichong(self):
        res = []
        # 使用 force_analysis_results 中的合化冲力量结果来调整五行力量
        if not self.force_analysis_results:
            # 如果没有合化冲力量，直接将原始的 bazi_power_chart 添加到结果列表中
            res.append(copy.deepcopy(self.bazi_power_chart))
        else:
            for result in self.force_analysis_results:
                tf = BaziChartPowerTransformerFromHehuichong()
                bazi_power_chart_prob = tf.transform(self.bazi_chart, self.bazi_power_chart, result, self.log_helper)
                res.append(bazi_power_chart_prob)
        return res

    def apply_monthling(self):
        # 获取月支的五行
        month_zhi_wuxing = self.bazi_chart.month_zhi._wuxing

        adjustments = {
            month_zhi_wuxing: 1 + MONTH_FORCE,
            Wuxing((month_zhi_wuxing.value + 1) % 5): 1 + MONTH_FORCE * 0.8,
            Wuxing((month_zhi_wuxing.value + 2) % 5): 1 - MONTH_FORCE * 0.75,
            Wuxing((month_zhi_wuxing.value + 3) % 5): 1 - MONTH_FORCE * 0.6,
            Wuxing((month_zhi_wuxing.value + 4) % 5): 1 - MONTH_FORCE * 0.45
        }

        # 更新每个 BaziPowerChartElement 的 wuxing_power
        for element in self.bazi_power_chart.fixed_row:
            for wuxing, factor in adjustments.items():
                element.wuxing_power[wuxing] *= factor

        for sublist in self.bazi_power_chart.variable_row:
            for element in sublist:
                for wuxing, factor in adjustments.items():
                    element.wuxing_power[wuxing] *= factor

        return self.bazi_power_chart

    def apply_tiantoudicang(self, bazi_power_chart, time=0):
        state1 = bazi_power_chart
        state2 = copy.deepcopy(bazi_power_chart)
        word = []
        wuxing_word = []
        # 对天干进行处理
        for i, element_gan in enumerate(state2.fixed_row):
            force_sum = 0
            gan_name = zhu_name[i] + '干' + self.bazi_chart.gan_list[i]._chinese_name + self.bazi_chart.gan_list[i]._wuxing_chinese_name
            zhi_name = []
            for j, elements_zhi in enumerate(state1.variable_row):
                force = sum(element.M * element.wuxing_power[element_gan.gan.wuxing] for element in elements_zhi)
                rate = 1 - 0.2 * abs(i - j)
                force_sum += force * rate * TIANTOUDICANG_FORCE
                for k in range(len(elements_zhi)):
                    if elements_zhi[k].gan.wuxing == element_gan.gan.wuxing and elements_zhi[k].wuxing_power[element_gan.gan.wuxing] > 0:
                        zhi_name.append(zhu_name[j] + '支' + self.bazi_chart.zhi_list[j]._chinese_name + '中' + elements_zhi[k].gan.chinese_name + elements_zhi[k].gan.wuxing.chinese_name)
                        wuxing_word.append(self.bazi_chart.gan_list[i]._wuxing.chinese_name)
            element_gan.wuxing_power[element_gan.gan.wuxing] *= (force_sum + 1)
            log = gan_name + '通根于' + '、'.join(zhi_name)
            word.append(log)
        # 使用 Counter 计算每个元素的出现次数
        wuxing_count = Counter(wuxing_word)
        sorted_unique_wuxing = [item for item, count in wuxing_count.most_common()]
        if time == 0:
            log_all = '\n【天透地藏分析】：\n' + '；\n'.join(word) + '。\n原局中五行' + '、'.join(sorted_unique_wuxing) + '的力量增强。\n'
            self.log_helper.info(log_all)

        # 对地支进行处理
        for i, elements_zhi in enumerate(state2.variable_row):
            for element in elements_zhi:
                force_sum = 0
                for j, element_gan in enumerate(state1.fixed_row):
                    force = element_gan.M * element_gan.wuxing_power[element.gan.wuxing]
                    rate = 1 - 0.2 * abs(i - j)
                    force_sum += force * rate * TIANTOUDICANG_FORCE
                element.wuxing_power[element.gan.wuxing] *= (force_sum + 1)

        return state2

    def apply_shengke(self, bazi_power_chart):
        tf = BaziChartPowerTransformerFromShengke()
        return tf.update_state(bazi_power_chart)

    def get_average_bazi_power_chart(self, bazi_power_charts):
        if not bazi_power_charts:
            return None

        # 初始化一个新的 BaziPowerChart 用于存储平均值
        average_bazi_power_chart = copy.deepcopy(bazi_power_charts[0])
        num_charts = len(bazi_power_charts)

        # 计算 fixed_row 的平均值
        for i in range(len(average_bazi_power_chart.fixed_row)):
            for wuxing in Wuxing:
                sum_power = sum(chart.fixed_row[i].wuxing_power[wuxing] for chart in bazi_power_charts)
                average_bazi_power_chart.fixed_row[i].wuxing_power[wuxing] = sum_power / num_charts

        # 计算 variable_row 的平均值
        for i in range(len(average_bazi_power_chart.variable_row)):
            for j in range(len(average_bazi_power_chart.variable_row[i])):
                for wuxing in Wuxing:
                    sum_power = sum(chart.variable_row[i][j].wuxing_power[wuxing] for chart in bazi_power_charts)
                    average_bazi_power_chart.variable_row[i][j].wuxing_power[wuxing] = sum_power / num_charts

        return average_bazi_power_chart

    def transform(self):
        # 1. 先应用月令对五行力量的影响
        self.apply_monthling()

        # 2. 应用合化冲分析
        bazi_power_chart_prob_list = self.apply_hehuichong()

        # 3. 应用其他方法：天透地藏和生克
        for i in range(len(bazi_power_chart_prob_list)):
            bazi_power_chart_prob_list[i] = self.apply_tiantoudicang(bazi_power_chart_prob_list[i])
            bazi_power_chart_prob_list[i] = self.apply_shengke(bazi_power_chart_prob_list[i])

        # 4. 计算最终的平均力量图
        outcome = self.get_average_bazi_power_chart(bazi_power_chart_prob_list)

        return outcome

class BaziChartPowerTransformerFromHehuichong:
    def transform(self, bazi_chart, bazi_power_chart, forces, log_helper):
        self.bazi_chart = bazi_chart
        self.bazi_power_chart = copy.deepcopy(bazi_power_chart)
        self.forces = forces

        he_forces = [force for force in self.forces if isinstance(force, TianGanHe)]
        chong_forces = [force for force in self.forces if isinstance(force, TianGanChong)]
        sanhui_forces = [force for force in self.forces if isinstance(force, DiZhiSanHui)]
        sanhe_forces = [force for force in self.forces if isinstance(force, DiZhiSanHe)]
        banhe_forces = [force for force in self.forces if isinstance(force, DiZhiBanHe)]
        liuhe_forces = [force for force in self.forces if isinstance(force, DiZhiLiuHe)]
        liuchong_forces = [force for force in self.forces if isinstance(force, DiZhiLiuChong)]
        
        # 处理天干五合和天干相冲
        for he_force in he_forces:
            related_chong_forces = [chong_force for chong_force in chong_forces if set(chong_force.element_index).intersection(he_force.element_index)]
            if related_chong_forces:
                for chong_force in related_chong_forces:
                    x = he_force.E - chong_force.E
                    if he_force.is_hua:
                        self.apply_tiangan_he_with_hua_and_chong(he_force, x)
                    else:
                        self.apply_tiangan_he_without_hua_and_chong(he_force, x)
                    chong_forces.remove(chong_force)  # 移除已处理的相冲力
            else:
                if he_force.is_hua:
                    self.apply_tiangan_he_with_hua(he_force)
                else:
                    self.apply_tiangan_he_without_hua(he_force)
        
        # 处理剩余的天干相冲
        for chong_force in chong_forces:
            self.apply_tiangan_chong(chong_force)
        
        # 处理地支三会
        for sanhui_force in sanhui_forces:
            self.apply_dizhi_sanhui(sanhui_force)
        
        # 处理地支三合
        for sanhe_force in sanhe_forces:
            self.apply_dizhi_sanhe(sanhe_force)
        
        # 处理地支半合
        for banhe_force in banhe_forces:
            self.apply_dizhi_banhe(banhe_force)

        # 处理地支六合
        for liuhe_force in liuhe_forces:
            self.apply_dizhi_liuhe(liuhe_force)

        # 处理地支六冲
        for liuchong_force in liuchong_forces:
            self.apply_dizhi_liuchong(liuchong_force)

        return self.bazi_power_chart

    def apply_tiangan_he_with_hua(self, force):
        for index in force.element_index:
            element = self.bazi_power_chart.get_element(force.field, index)
            original_wuxing = element.gan.wuxing
            element.wuxing_power[original_wuxing] *= (1 - force.E)
            element.wuxing_power[force.wuxing] = max(element.wuxing_power.get(original_wuxing, 0) * force.E, 0)

    def _is_de_ling(self, gan_wuxing, month_zhi):
        """
        判断天干是否得令
        甲乙木：寅卯辰月得令
        丙丁火：巳午未月得令
        戊己土：辰戌丑未月得令
        庚辛金：申酉戌月得令
        壬癸水：亥子丑月得令
        """
        month_zhi_enum = month_zhi._zhi if hasattr(month_zhi, '_zhi') else month_zhi
        
        de_ling_map = {
            Wuxing.MU: [Zhi.YIN, Zhi.MAO, Zhi.CHEN],      # 甲乙木：寅卯辰月得令
            Wuxing.HUO: [Zhi.SI, Zhi.WU, Zhi.WEI],       # 丙丁火：巳午未月得令
            Wuxing.TU: [Zhi.CHEN, Zhi.XU, Zhi.CHOU, Zhi.WEI],  # 戊己土：辰戌丑未月得令
            Wuxing.JIN: [Zhi.SHEN, Zhi.YOU, Zhi.XU],     # 庚辛金：申酉戌月得令
            Wuxing.SHUI: [Zhi.HAI, Zhi.ZI, Zhi.CHOU]     # 壬癸水：亥子丑月得令
        }
        
        return month_zhi_enum in de_ling_map.get(gan_wuxing, [])

    def apply_tiangan_he_without_hua(self, force):
        """
        处理天干合而不化的情况
        如果合化双方有一方得令，而另一方不得令：
        - 得令方：不损失力量（保持原值）
        - 失令方：双倍损失力量（损失 2 * E）
        如果双方都得令或都不得令：按原来的逻辑，都损失 E
        """
        month_zhi = self.bazi_chart.month_zhi
        
        # 获取两个天干的元素和五行
        element1 = self.bazi_power_chart.get_element(force.field, force.element_index[0])
        element2 = self.bazi_power_chart.get_element(force.field, force.element_index[1])
        wuxing1 = element1.gan.wuxing
        wuxing2 = element2.gan.wuxing
        
        # 判断是否得令
        de_ling1 = self._is_de_ling(wuxing1, month_zhi)
        de_ling2 = self._is_de_ling(wuxing2, month_zhi)
        
        # 根据得令情况调整力量损失
        if de_ling1 and not de_ling2:
            # 第一个得令，第二个失令
            # 第一个：不损失力量
            # 第二个：双倍损失力量
            element1.wuxing_power[wuxing1] = element1.wuxing_power[wuxing1]  # 保持不变
            element2.wuxing_power[wuxing2] = max(element2.wuxing_power[wuxing2] * (1 - 2 * force.E), 0)
        elif de_ling2 and not de_ling1:
            # 第二个得令，第一个失令
            # 第一个：双倍损失力量
            # 第二个：不损失力量
            element1.wuxing_power[wuxing1] = max(element1.wuxing_power[wuxing1] * (1 - 2 * force.E), 0)
            element2.wuxing_power[wuxing2] = element2.wuxing_power[wuxing2]  # 保持不变
        else:
            # 双方都得令或都不得令：按原来的逻辑，都损失 E
            element1.wuxing_power[wuxing1] = max(element1.wuxing_power[wuxing1] * (1 - force.E), 0)
            element2.wuxing_power[wuxing2] = max(element2.wuxing_power[wuxing2] * (1 - force.E), 0)

    def apply_tiangan_he_with_hua_and_chong(self, force, x):
        for index in force.element_index:
            element = self.bazi_power_chart.get_element(force.field, index)
            original_wuxing = element.gan.wuxing
            element.wuxing_power[force.wuxing] = max(element.wuxing_power.get(original_wuxing, 0) * x, 0)
            element.wuxing_power[original_wuxing] = max(element.wuxing_power[original_wuxing] * (1 - x), 0)

    def apply_tiangan_he_without_hua_and_chong(self, force, x):
        for index in force.element_index:
            element = self.bazi_power_chart.get_element(force.field, index)
            original_wuxing = element.gan.wuxing
            element.wuxing_power[original_wuxing] = max(element.wuxing_power[original_wuxing] * (1 - x), 0)

    def apply_tiangan_chong(self, force):
        for index in force.element_index:
            element = self.bazi_power_chart.get_element(force.field, index)
            original_wuxing = element.gan.wuxing
            element.wuxing_power[original_wuxing] = max(element.wuxing_power[original_wuxing] * (1 - force.E), 0)
    
    def apply_dizhi_sanhui(self, force):
        for index in force.element_index:
            elements = self.bazi_power_chart.get_element(force.field, index)
            for element in elements:
                for wuxing in element.wuxing_power:
                    if wuxing != force.wuxing:
                        element.wuxing_power[wuxing] = 0
                element.wuxing_power[force.wuxing] = SANHUI_FORCE
    
    def apply_dizhi_sanhe(self, force):
        specific_gans = {
            Zhi.YIN: [Gan.BING],
            Zhi.SHEN: [Gan.REN],
            Zhi.SI: [Gan.GENG],
            Zhi.HAI: [Gan.JIA],
            Zhi.ZI: [Gan.GUI],
            Zhi.WU: [Gan.DING],
            Zhi.MAO: [Gan.YI],
            Zhi.YOU: [Gan.XIN],
            Zhi.CHOU: [Gan.XIN],
            Zhi.CHEN: [Gan.GUI],
            Zhi.WEI: [Gan.YI],
            Zhi.XU: [Gan.DING]
        }
        for index in force.element_index:
            elements = self.bazi_power_chart.get_element(force.field, index)
            zhi = self.bazi_chart.get_zhi_by_index(index)
            for element in elements:
                if element.gan in specific_gans.get(zhi, []):
                    element.wuxing_power[force.wuxing] = SANHE_FORCE

    def apply_dizhi_banhe(self, force):
        specific_gans = {
            Zhi.YIN: [Gan.BING],
            Zhi.SHEN: [Gan.REN],
            Zhi.SI: [Gan.GENG],
            Zhi.HAI: [Gan.JIA],
            Zhi.ZI: [Gan.GUI],
            Zhi.WU: [Gan.DING],
            Zhi.MAO: [Gan.YI],
            Zhi.YOU: [Gan.XIN],
            Zhi.CHOU: [Gan.XIN],
            Zhi.CHEN: [Gan.GUI],
            Zhi.WEI: [Gan.YI],
            Zhi.XU: [Gan.DING]
        }
        for index in force.element_index:
            elements = self.bazi_power_chart.get_element(force.field, index)
            zhi = self.bazi_chart.get_zhi_by_index(index)
            for element in elements:
                if element.gan in specific_gans.get(zhi, []):
                    element.wuxing_power[force.wuxing] = SANHE_FORCE

    def apply_dizhi_liuhe(self, force):
        for index in force.element_index:
            elements = self.bazi_power_chart.get_element(force.field, index)
            for element in elements:
                original_wuxing = element.gan.wuxing
                a = force.E * element.wuxing_power[original_wuxing]
                element.wuxing_power[force.wuxing] += a
                element.wuxing_power[original_wuxing] -= a
                if element.wuxing_power[original_wuxing] < 0:
                    element.wuxing_power[force.wuxing] += element.wuxing_power[original_wuxing]
                    element.wuxing_power[original_wuxing] = 0

    def apply_dizhi_liuchong(self, force):
        chong_gan_map = {
            Gan.JIA: Gan.GENG,
            Gan.YI: Gan.XIN,
            Gan.BING: Gan.REN,
            Gan.DING: Gan.GUI,
            Gan.GENG: Gan.JIA,
            Gan.XIN: Gan.YI,
            Gan.REN: Gan.BING,
            Gan.GUI: Gan.DING
        }

        if len(force.element_index) != 2:
            raise ValueError("地支六冲应正好包含两个地支")

        index1, index2 = force.element_index
        elements1 = self.bazi_power_chart.get_element(force.field, index1)
        elements2 = self.bazi_power_chart.get_element(force.field, index2)

        for element1 in elements1:
            chong_gan = chong_gan_map.get(element1.gan)
            if chong_gan:
                for element2 in elements2:
                    if element2.gan == chong_gan:
                        if element1.M <= element2.M:
                            a, b = element1.M, element2.M
                            element1.wuxing_power[element1.gan.wuxing] = max(element1.wuxing_power[element1.gan.wuxing] * (1 - force.E), 0)
                            element2.wuxing_power[chong_gan.wuxing] = max(element2.wuxing_power[chong_gan.wuxing] * (1 - (a * force.E) / b), 0)
                        else:
                            a, b = element2.M, element1.M
                            element1.wuxing_power[element1.gan.wuxing] = max(element1.wuxing_power[element1.gan.wuxing] * (1 - (a * force.E) / b), 0)
                            element2.wuxing_power[chong_gan.wuxing] = max(element2.wuxing_power[chong_gan.wuxing] * (1 - force.E), 0)

class BaziChartPowerTransformerFromShengke:
    def calculate_total_force(self, bazi_power_chart):
        fixed_row = bazi_power_chart.fixed_row
        variable_row = bazi_power_chart.variable_row
        rows, cols = 2, len(bazi_power_chart.fixed_row)

        total_forces_fixed = [{wuxing: 0 for wuxing in Wuxing} for _ in range(cols)]
        total_forces_variable = [[{wuxing: 0 for wuxing in Wuxing} for _ in range(len(variable_row[i]))] for i in range(cols)]

        # 计算地支对天干的影响
        for i, element_gan in enumerate(fixed_row):
            for j, elements_zhi in enumerate(variable_row):
                distance = manhattan_distance((0, i), (1, j))
                for element in elements_zhi:
                    for wuxing in Wuxing:
                        force = calculate_force(element, wuxing, distance)
                        total_forces_fixed[i][wuxing] += force

        # 计算天干对地支的影响
        for i, elements_zhi in enumerate(variable_row):
            for j, element in enumerate(elements_zhi):
                for k, element_gan in enumerate(fixed_row):
                    distance = manhattan_distance((1, i), (0, k))
                    for wuxing in Wuxing:
                        force = calculate_force(element_gan, wuxing, distance)
                        total_forces_variable[i][j][wuxing] += force

        # 计算地支之间的影响
        for i, elements_zhi in enumerate(variable_row):
            for j, element in enumerate(elements_zhi):
                for k, other_elements_zhi in enumerate(variable_row):
                    if i != k:
                        for other_element in other_elements_zhi:
                            distance = manhattan_distance((1, i), (1, k))
                            for wuxing in Wuxing:
                                force = calculate_force(other_element, wuxing, distance)
                                total_forces_variable[i][j][wuxing] += force

        # 计算天干之间的影响
        for i, element_gan in enumerate(fixed_row):
            for j, other_element_gan in enumerate(fixed_row):
                if i != j:
                    distance = manhattan_distance((0, i), (0, j))
                    for wuxing in Wuxing:
                        force = calculate_force(other_element_gan, wuxing, distance)
                        total_forces_fixed[i][wuxing] += force

        return total_forces_fixed, total_forces_variable

    def update_state(self, bazi_power_chart):
        state1 = bazi_power_chart
        state2 = copy.deepcopy(bazi_power_chart)
        fixed_row = state2.fixed_row
        variable_row = state2.variable_row

        total_forces_fixed, total_forces_variable = self.calculate_total_force(state1)

        # 更新天干的五行力量
        for i, element_gan in enumerate(fixed_row):
            for wuxing in Wuxing:
                force = total_forces_fixed[i][wuxing]
                element_gan.wuxing_power[wuxing] = max(element_gan.wuxing_power[wuxing] * max(1 + (
                    force + 0.8 * total_forces_fixed[i][Wuxing((wuxing.value - 1) % 5)]
                    - total_forces_fixed[i][Wuxing((wuxing.value - 2) % 5)] * 0.75
                    - total_forces_fixed[i][Wuxing((wuxing.value - 3) % 5)] * 0.6
                    - total_forces_fixed[i][Wuxing((wuxing.value - 4) % 5)] * 0.45
                ) * SHENGKE_FORCE, 0), 0)

        # 更新地支的五行力量
        for i, elements_zhi in enumerate(variable_row):
            for j, element in enumerate(elements_zhi):
                for wuxing in Wuxing:
                    force = total_forces_variable[i][j][wuxing]
                    element.wuxing_power[wuxing] = max(element.wuxing_power[wuxing] * max(1 + (
                        force + 0.8 * total_forces_variable[i][j][Wuxing((wuxing.value - 1) % 5)]
                        - total_forces_variable[i][j][Wuxing((wuxing.value - 2) % 5)] * 0.75
                        - total_forces_variable[i][j][Wuxing((wuxing.value - 3) % 5)] * 0.6
                        - total_forces_variable[i][j][Wuxing((wuxing.value - 4) % 5)] * 0.45
                    ) * SHENGKE_FORCE, 0), 0)

        return state2

