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

# analysis/hehua/hehua_power_check_analyser.py

from typing import List, Dict, Any

from .force import Force
from ..base_analyser import BaseAnalyser
from ..hehua.force import (
    DiZhiSanHui,
    DiZhiSanHe,
    DiZhiBanHe,
    DiZhiLiuHe,
    DiZhiLiuChong,
    TianGanHe,
    TianGanChong
)
from ..hehua.hehuichong_force_calculator import HehuichongForceCalculator
from ...core.property import Wuxing, Gan, Zhi

# 设置全局力量值
TianGanHeWithoutHuaPowerValue = 0.48
TianGanHeWithHuaPowerValue = 0.8
TianGanChongDistanceOnePowerValue = 0.5
TianGanChongDistanceTwoPowerValue = 0.125
TianGanChongDistanceThreePowerValue = 0.06

DiZhiSanHuiPowerValue = 2
DiZhiSanHePowerValue = 1.5
DiZhiBanHeDistanceOnePowerValue = 0.4
DiZhiBanHeDistanceTwoPowerValue = 0.1
DiZhiBanHeDistanceThreePowerValue = 0
DiZhiLiuHeWithHuaPowerValue = 0.2
DiZhiLiuHeWithoutHuaPowerValue = 0.1

# 地支六冲的力量值
DiZhiLiuChongDistanceOnePowerValue = [1, 0.8, 0.5]
DiZhiLiuChongDistanceTwoPowerValue = [0.25, 0.2, 0.125]
DiZhiLiuChongDistanceThreePowerValue = [0.11, 0.088, 0.055]

class HehuaPowerCheckAnalyser(BaseAnalyser):
    def __init__(self, bazi_chart, hehua_check_results, log_helper):
        super().__init__(bazi_chart, log_helper)
        self.without_time = self._bazi_chart.without_time
        self._hehua_check_results: Dict[str, List[Any]] = hehua_check_results
        if self.without_time:
            self._zhi_list: List[Zhi] = [
                self._bazi_chart.year_zhi,
                self._bazi_chart.month_zhi,
                self._bazi_chart.day_zhi
            ]
            self._gan_list: List[Gan] = [
                self._bazi_chart.year_gan,
                self._bazi_chart.month_gan,
                self._bazi_chart.day_gan
            ]
        else:
            self._zhi_list: List[Zhi] = [
                self._bazi_chart.year_zhi,
                self._bazi_chart.month_zhi,
                self._bazi_chart.day_zhi,
                self._bazi_chart.hour_zhi
            ]
            self._gan_list: List[Gan] = [
                self._bazi_chart.year_gan,
                self._bazi_chart.month_gan,
                self._bazi_chart.day_gan,
                self._bazi_chart.hour_gan
            ]
        self._zhi_names: List[str] = [zhi._chinese_name for zhi in self._zhi_list]
        self._gan_names: List[str] = [gan._chinese_name for gan in self._gan_list]

    def analyse(self) -> Dict[str, List[Force]]:
        forces = []

        # 地支三会
        forces += self._calculate_dizhi_sanhui_forces()

        # 地支三合
        forces += self._calculate_dizhi_sanhe_forces()

        # 地支半合
        forces += self._calculate_dizhi_banhe_forces()

        # 地支六合
        forces += self._calculate_dizhi_liuhe_forces()

        # 地支六冲
        forces += self._calculate_dizhi_liuchong_forces()

        # 天干五合
        gan_forces = self._calculate_tiangan_he_forces()

        # 天干相冲
        gan_forces += self._calculate_tiangan_chong_forces()

        # 调用 HehuichongForceCalculator 筛选出最终成立的地支作用力
        force_calculator = HehuichongForceCalculator()
        valid_zhi_forces_list = force_calculator.find_valid_forces(self._zhi_list, forces)

        # 合并天干和地支的作用力结果
        combined_forces_list = []
        for valid_zhi_forces in valid_zhi_forces_list:
            combined_forces_list.append(list(valid_zhi_forces) + gan_forces)
        
        hehua_dict = {}
        for force_list in combined_forces_list:
            for force in force_list:
                force_name = force.get_cate()
                if force_name not in hehua_dict:
                    hehua_dict[force_name] = []
                hehua_dict[force_name].append(force)
    
        # 记录有效的合化力量组合
        formatted_log = self._format_valid_forces_log(combined_forces_list)
        self._log_helper.debug("有效的合化冲力量组合：\n" + formatted_log)
        
        return hehua_dict

    # 以下是各个力量计算方法，使用之前的逻辑

    def _calculate_dizhi_sanhui_forces(self) -> List[DiZhiSanHui]:
        di_zhi_san_hui_combinations = {
            frozenset(["寅", "卯", "辰"]): Wuxing.MU,
            frozenset(["巳", "午", "未"]): Wuxing.HUO,
            frozenset(["申", "酉", "戌"]): Wuxing.JIN,
            frozenset(["亥", "子", "丑"]): Wuxing.SHUI
        }
        forces = []
        di_zhi_san_hui_results = self._hehua_check_results.get('地支三会', [])
        for result in di_zhi_san_hui_results:
            zhi_set = frozenset([self._zhi_names[i] for i in result])
            if zhi_set in di_zhi_san_hui_combinations:
                wuxing = di_zhi_san_hui_combinations[zhi_set]
                forces.append(
                    DiZhiSanHui(
                        [self._zhi_list[i] for i in result],
                        result,
                        wuxing,
                        DiZhiSanHuiPowerValue
                    )
                )
        self._log_helper.debug(f"地支三会：{forces if len(forces) > 0 else '无'}")
        return forces

    def _calculate_dizhi_sanhe_forces(self) -> List[DiZhiSanHe]:
        di_zhi_san_he_combinations = {
            frozenset(["亥", "卯", "未"]): Wuxing.MU,
            frozenset(["寅", "午", "戌"]): Wuxing.HUO,
            frozenset(["巳", "酉", "丑"]): Wuxing.JIN,
            frozenset(["申", "子", "辰"]): Wuxing.SHUI
        }
        forces = []
        di_zhi_san_he_results = self._hehua_check_results.get('地支三合', [])
        for result in di_zhi_san_he_results:
            zhi_set = frozenset([self._zhi_names[i] for i in result])
            if zhi_set in di_zhi_san_he_combinations:
                wuxing = di_zhi_san_he_combinations[zhi_set]
                forces.append(
                    DiZhiSanHe(
                        [self._zhi_list[i] for i in result],
                        result,
                        wuxing,
                        DiZhiSanHePowerValue
                    )
                )
        self._log_helper.debug(f"地支三合：{forces if len(forces) > 0 else '无'}")
        return forces

    def _calculate_dizhi_banhe_forces(self) -> List[DiZhiBanHe]:
        di_zhi_ban_he_combinations = {
            frozenset(["寅", "午"]): Wuxing.HUO,
            frozenset(["午", "戌"]): Wuxing.HUO,
            frozenset(["巳", "酉"]): Wuxing.JIN,
            frozenset(["酉", "丑"]): Wuxing.JIN,
            frozenset(["申", "子"]): Wuxing.SHUI,
            frozenset(["子", "辰"]): Wuxing.SHUI,
            frozenset(["亥", "卯"]): Wuxing.MU,
            frozenset(["卯", "未"]): Wuxing.MU
        }
        forces = []
        di_zhi_ban_he_results = self._hehua_check_results.get('地支半合', [])
        for result in di_zhi_ban_he_results:
            zhi_set = frozenset([self._zhi_names[i] for i in result])
            if zhi_set in di_zhi_ban_he_combinations:
                wuxing = di_zhi_ban_he_combinations[zhi_set]
                distance = abs(result[0] - result[1])
                if distance == 1:
                    power = DiZhiBanHeDistanceOnePowerValue
                elif distance == 2:
                    power = DiZhiBanHeDistanceTwoPowerValue
                elif distance == 3:
                    power = DiZhiBanHeDistanceThreePowerValue
                else:
                    power = 0.0  # 超过范围，力量为0
                forces.append(
                    DiZhiBanHe(
                        [self._zhi_list[i] for i in result],
                        result,
                        wuxing,
                        distance,
                        power
                    )
                )
        self._log_helper.debug(f"地支半合：{forces if len(forces) > 0 else '无'}")
        return forces

    def _calculate_dizhi_liuhe_forces(self) -> List[DiZhiLiuHe]:
        di_zhi_liu_he_combinations = {
            frozenset(["子", "丑"]): Wuxing.TU,
            frozenset(["寅", "亥"]): Wuxing.MU,
            frozenset(["卯", "戌"]): Wuxing.HUO,
            frozenset(["辰", "酉"]): Wuxing.JIN,
            frozenset(["巳", "申"]): Wuxing.SHUI,
            frozenset(["午", "未"]): Wuxing.TU
        }
        forces = []
        di_zhi_liu_he_results = self._hehua_check_results.get('地支六合', [])
        for result in di_zhi_liu_he_results:
            zhi_set = frozenset([self._zhi_names[i] for i in result])
            if zhi_set in di_zhi_liu_he_combinations and abs(result[0] - result[1]) == 1:
                wuxing = di_zhi_liu_he_combinations[zhi_set]
                is_hua = self._check_dizhi_liuhe_transformation(wuxing, result)
                power = DiZhiLiuHeWithHuaPowerValue if is_hua else DiZhiLiuHeWithoutHuaPowerValue
                forces.append(
                    DiZhiLiuHe(
                        [self._zhi_list[i] for i in result],
                        result,
                        wuxing,
                        is_hua,
                        power
                    )
                )
        self._log_helper.debug(f"地支六合：{forces if len(forces) > 0 else '无'}")
        return forces

    def _calculate_dizhi_liuchong_forces(self) -> List[DiZhiLiuChong]:
        di_zhi_liu_chong_combinations = {
            frozenset(["子", "午"]), frozenset(["卯", "酉"]),
            frozenset(["寅", "申"]), frozenset(["巳", "亥"]),
            frozenset(["辰", "戌"]), frozenset(["丑", "未"])
        }
        forces = []
        di_zhi_liu_chong_results = self._hehua_check_results.get('地支六冲', [])
        for result in di_zhi_liu_chong_results:
            zhi_set = frozenset([self._zhi_names[i] for i in result])
            if zhi_set in di_zhi_liu_chong_combinations:
                distance = abs(result[0] - result[1])
                if zhi_set == frozenset(["子", "午"]) or zhi_set == frozenset(["卯", "酉"]):
                    index = 0
                elif zhi_set == frozenset(["寅", "申"]) or zhi_set == frozenset(["巳", "亥"]):
                    index = 1
                elif zhi_set == frozenset(["辰", "戌"]) or zhi_set == frozenset(["丑", "未"]):
                    index = 2
                else:
                    index = 0  # 默认值

                if distance == 1:
                    power = DiZhiLiuChongDistanceOnePowerValue[index]
                elif distance == 2:
                    power = DiZhiLiuChongDistanceTwoPowerValue[index]
                elif distance == 3:
                    power = DiZhiLiuChongDistanceThreePowerValue[index]
                else:
                    power = 0.0  # 超过范围，力量为0

                forces.append(
                    DiZhiLiuChong(
                        [self._zhi_list[i] for i in result],
                        result,
                        distance,
                        power
                    )
                )
        self._log_helper.debug(f"地支六冲：{forces if len(forces) > 0 else '无'}")
        return forces

    def _calculate_tiangan_he_forces(self) -> List[TianGanHe]:
        tian_gan_he_combinations = {
            frozenset([Gan.JIA, Gan.JI]): Wuxing.TU,
            frozenset([Gan.YI, Gan.GENG]): Wuxing.JIN,
            frozenset([Gan.BING, Gan.XIN]): Wuxing.SHUI,
            frozenset([Gan.DING, Gan.REN]): Wuxing.MU,
            frozenset([Gan.WU, Gan.GUI]): Wuxing.HUO
        }
        forces = []
        tian_gan_he_results = self._hehua_check_results.get('天干五合', [])
        for result in tian_gan_he_results:
            gan_set = frozenset([self._gan_list[result[0]].get(), self._gan_list[result[1]].get()])
            if gan_set in tian_gan_he_combinations and all(i in [0, 1] for i in result):
                wuxing = tian_gan_he_combinations[gan_set]
                is_hua = self._check_tiangan_hehua_transformation(wuxing)
                power = TianGanHeWithHuaPowerValue if is_hua else TianGanHeWithoutHuaPowerValue
                forces.append(
                    TianGanHe(
                        [self._gan_list[i] for i in result],
                        result,
                        wuxing,
                        is_hua,
                        power
                    )
                )
        self._log_helper.debug(f"天干五合：{forces if len(forces) > 0 else '无'}")
        return forces

    def _calculate_tiangan_chong_forces(self) -> List[TianGanChong]:
        tian_gan_chong_combinations = {
            frozenset([Gan.JIA, Gan.GENG]),
            frozenset([Gan.YI, Gan.XIN]),
            frozenset([Gan.BING, Gan.REN]),
            frozenset([Gan.DING, Gan.GUI])
        }
        forces = []
        tian_gan_chong_results = self._hehua_check_results.get('天干相冲', [])
        for result in tian_gan_chong_results:
            gan_set = frozenset([self._gan_list[result[0]].get(), self._gan_list[result[1]].get()])
            if gan_set in tian_gan_chong_combinations and self._gan_list.index(self._bazi_chart.day_gan) not in result:
                distance = abs(result[0] - result[1])
                if distance == 1:
                    power = TianGanChongDistanceOnePowerValue
                elif distance == 2:
                    power = TianGanChongDistanceTwoPowerValue
                elif distance == 3:
                    power = TianGanChongDistanceThreePowerValue
                else:
                    power = TianGanChongDistanceOnePowerValue / (distance ** 2)
                forces.append(
                    TianGanChong(
                        [self._gan_list[i] for i in result],
                        result,
                        distance,
                        power
                    )
                )
        self._log_helper.debug(f"天干六冲：{forces if len(forces) > 0 else '无'}")
        return forces

    def _check_dizhi_liuhe_transformation(self, wuxing, elements):
        month_zhi = self._bazi_chart.month_zhi
        transformation_conditions = {
            Wuxing.TU: ["丑", "辰", "未", "戌"],
            Wuxing.MU: ["寅", "卯"],
            Wuxing.HUO: ["巳", "午"],
            Wuxing.JIN: ["申", "酉"],
            Wuxing.SHUI: ["亥", "子"]
        }
        if month_zhi._chinese_name not in transformation_conditions[wuxing]:
            return False

        for i in elements:
            gan = self._gan_list[i]
            if gan._wuxing == wuxing:
                return True

        return False

    def _check_tiangan_hehua_transformation(self, wuxing):
        month_zhi = self._bazi_chart.month_zhi
        transformation_conditions = {
            Wuxing.TU: ["辰", "巳", "午", "未", "戌", "丑"],
            Wuxing.JIN: ["申", "酉", "戌", "丑", "辰"],
            Wuxing.SHUI: ["申", "酉", "亥", "子", "丑"],
            Wuxing.MU: ["寅", "卯", "辰", "亥", "子", "丑"],
            Wuxing.HUO: ["寅", "卯", "辰", "巳", "午", "未"]
        }
        return month_zhi._chinese_name in transformation_conditions.get(wuxing, [])

    def _format_valid_forces_log(self, combined_forces_list: List[List[Any]]) -> str:
        logs = []
        if len(combined_forces_list) > 1:
            log = "经过仔细斟酌，基于我目前的判断，原局天干地支的合化结果如下，可能存在多种情况："
            for i, forces in enumerate(combined_forces_list):
                log += f"\n情况 {i + 1}: " + self._get_log_from_forces(forces)
            logs.append(log)
        else:
            if combined_forces_list and combined_forces_list[0]:
                log = "经过仔细斟酌，基于我目前的判断，原局天干地支的合化冲结果如下："
                log += self._get_log_from_forces(combined_forces_list[0])
                logs.append(log)
            else:
                logs.append("暂无有效的合化冲力量组合。")
        return '\n'.join(logs)

    def _get_log_from_forces(self, forces_list):
        res = []
        for force in forces_list:
            res.append(force.get_log())
        return '；'.join(res)
