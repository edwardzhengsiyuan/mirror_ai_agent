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

# analysis/hehua/hehua_analysis.py

from typing import List, Dict, Tuple, Any

from .force import Force
from .hehua_check_analyser import HehuaCheckAnalyser
from .hehua_power_check_analyser import HehuaPowerCheckAnalyser
from ..base_analyser import BaseAnalyser
from ...core import BaziChart
from ...utils import LogHelper


def get_elements_by_index(a, b, c):
    return [a[i] + c for i in b if 0 <= i < len(a)]

class HehuaAnalysis(BaseAnalyser):
    def __init__(self, bazi_chart: BaziChart, log_helper: LogHelper):
        super().__init__(bazi_chart, log_helper)
        self.without_time = self._bazi_chart.without_time
        self.hehua_check_results: Dict[str, Any] = {}
        self.hehua_analysis_results: List[Any] = []

    def analyse(self) -> Tuple[Dict[str, Any], List[Force]]:
        # 初步检查合化冲关系
        self._log_helper.debug("初步分析合化冲开始：\n")
        hehua_checker = HehuaCheckAnalyser(self._bazi_chart, self._log_helper)
        self.hehua_check_results = hehua_checker.analyse()

        # 记录初步检查结果
        self._log_helper.debug("可能存在的合化冲关系：\n")
        for key, value in self.hehua_check_results.items():
            if value:
                for v in value:
                    if self.without_time:
                        loc_idx = get_elements_by_index(["年", "月", "日", "时"], v, key[1])
                    else:
                        loc_idx = get_elements_by_index(["年", "月", "日"], v, key[1])
                    if key[1] == "干":
                        ele = self._bazi_chart.gan_list
                    else:
                        ele = self._bazi_chart.zhi_list
                    ele_select = get_elements_by_index([x._chinese_name + x._wuxing_chinese_name for x in ele], v, "")
                    self._log_helper.debug(f"{key}: {key[3].join([x + y for x, y in zip(loc_idx, ele_select)])}\n")
            else:
                self._log_helper.debug(f"{key}: 无\n")
        self._log_helper.debug("初步分析合化冲关系完成。")

        self._log_helper.debug("深度分析合化冲关系开始：")
        # 计算合化冲力量，排除冲突
        hehua_power_checker = HehuaPowerCheckAnalyser(self._bazi_chart, self.hehua_check_results, self._log_helper)
        self.hehua_analysis_results = hehua_power_checker.analyse()

        # 记录最终合化冲分析结果
        self._log_helper.info("综合考虑之后认为最终成立的合化冲关系：\n")
        # NOTE: avoid printing raw dict (breaks JSON consumers / tests)
        for force_cate in self.hehua_analysis_results:
            for force in self.hehua_analysis_results[force_cate]:
                self._log_helper.info(force.get_log())
        if len(self.hehua_analysis_results) == 0:
            self._log_helper.info('无')
        self._log_helper.debug("深度分析合化冲关系完成。")

        return self.hehua_check_results, self.hehua_analysis_results



