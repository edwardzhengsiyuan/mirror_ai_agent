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

# analysis/power/power_analysis.py

from typing import Any

from .bazi_power_chart import BaziPowerChart
from .power_transformer import PowerTransformer
from ..base_analyser import BaseAnalyser
from ...core import (
    BaziChart,
    get_gan_wuxing_yinyang
)
from ...utils import LogHelper


class PowerAnalysis(BaseAnalyser):
    def __init__(self, bazi_chart: BaziChart, log_helper: LogHelper, force_analysis_results):
        super().__init__(bazi_chart, log_helper)
        self._force_analysis_results: Any = force_analysis_results  # 根据实际类型替换 Any
        self._transformed_power_chart: Any = None  # 根据实际类型替换 Any

    def analyse(self) -> Any:  # 根据实际返回类型替换 Any
        # Step 1: 初始化 BaziPowerChart，不进行力量计算
        bazi_power_chart = BaziPowerChart(self._bazi_chart, self._force_analysis_results)

        # Step 2: 创建 PowerTransformer，并将 HehuaAnalysis 结果传入
        transformer = PowerTransformer(self._bazi_chart, bazi_power_chart, self._force_analysis_results, self._log_helper)
        transformed_power_chart = transformer.transform()

        # Step 3: 在 transformations 完成后，调用 calculate_powers 计算五行和十神的力量
        transformed_power_chart.calculate_powers()

        # Step 4: 返回最终的力量分析结果
        # 计算日主强弱
        rizhu_strength = transformed_power_chart.rizhu_strength
        self._log_helper.info("【日主身强身弱分析】：\n")
        if rizhu_strength > 0:
            if rizhu_strength > 1:
                transformed_power_chart.shenqiangruo = "日主强\n"
            else:
                transformed_power_chart.shenqiangruo = "日主中和\n"
        else:
            if rizhu_strength < -1:
                transformed_power_chart.shenqiangruo = "日主弱\n"
            else:
                transformed_power_chart.shenqiangruo = "日主中和\n"
        self._log_helper.info(transformed_power_chart.shenqiangruo)

        # 记录五行力量比例
        self._log_helper.info("【五行力量比例】：\n")
        for wuxing, proportion in transformed_power_chart.wuxing_proportions.items():
            self._log_helper.info(f"{wuxing.chinese_name}: {proportion:.2%}\n")

        # 记录十神力量比例
        self._log_helper.info("【十神力量比例】：\n")
        for shishen, proportion in transformed_power_chart.shishen_proportions.items():
            self._log_helper.info(f"{shishen.chinese_name}: {proportion:.2%}\n")

        return transformed_power_chart
    
    def check_wuxing_power(self, transformed_power_chart):
        for wuxing, proportion in transformed_power_chart.wuxing_proportions.items():
            if proportion >= 0.9:
                self._bazi_chart.is_special = True
                rizhu_wuxing = self._bazi_chart.day_gan.get().wuxing
                wuxing_dis = (wuxing - rizhu_wuxing) % 5
                if wuxing_dis in [0, 1, 2]:
                    self._bazi_chart.refer = get_gan_wuxing_yinyang(wuxing, 1 - self._bazi_chart.day_gan.get().yinyang)
                else:
                    self._bazi_chart.refer = get_gan_wuxing_yinyang(wuxing, self._bazi_chart.day_gan.get().yinyang)
                return
        temp = 0
        for wuxing, proportion in transformed_power_chart.wuxing_proportions.items():
            if proportion >= 0.35:
                temp += 1
        if temp > 1:
            self._bazi_chart.is_special = True


