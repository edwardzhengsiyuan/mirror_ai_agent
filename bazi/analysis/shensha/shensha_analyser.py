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

# analysis/shensha/shensha_analyser.py

from typing import List, Dict, Any, Tuple

from ..base_analyser import BaseAnalyser
from ..shensha import (
    Guchen,
    Guasu,
    Hongluan,
    Tianxi,
    Tiandeguiren,
    Yuede,
    Tianyi,
    Wenchang,
    Yangren,
    Lushen,
    Hongyan,
    Jiangxing,
    Huagai,
    Yima,
    Jiesha,
    Wangshen,
    Taohua,
    Taijiguiren,
    Kongwang,
    SanqiGuiren,
    FuxingGuiren,
    Kuigang,
    GuoyinGuiren,
    DexiuGuiren,
    Xuetang,
    Ciguan,
    TianchuGuiren,
    Jinyu,
    Zaisha,
    Bazhuan,
    Tongzi,
    Yinchayancuo,
    ShieDabai,
    Tianyii,
    Shensha
)
from ...core.bazi_chart import BaziChart
from ...utils import LogHelper


class ShenShaAnalyser(BaseAnalyser):
    def __init__(self, bazi_chart: BaziChart, log_helper: LogHelper):
        super().__init__(bazi_chart, log_helper)
        self.without_time = self._bazi_chart.without_time
        self._shensha_list: List[Dict[str, Any]] = []
        self._shensha_instances = self._initialize_shensha_instances()

    def _initialize_shensha_instances(self) -> List[Shensha]:
        self._log_helper.info("【神煞分析】：\n")
        return [
            Guchen(), Guasu(), Hongluan(), Tianxi(), Tiandeguiren(),
            Yuede(), Tianyi(), Wenchang(), Yangren(), Lushen(),
            Hongyan(), Jiangxing(), Huagai(), Yima(), Jiesha(),
            Wangshen(), Taohua(), Taijiguiren(), Kongwang(),
            SanqiGuiren(), FuxingGuiren(), Kuigang(), GuoyinGuiren(),
            DexiuGuiren(), Xuetang(), Ciguan(), TianchuGuiren(),
            Jinyu(), Zaisha(), Bazhuan(), Tongzi(), Yinchayancuo(), ShieDabai(),
            Tianyii()
        ]

    def analyse(self) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
        if (self.without_time):
            positions = {self._bazi_chart.year_zhu: '年柱', self._bazi_chart.month_zhu: '月柱',
                     self._bazi_chart.day_zhu: '日柱'}
        else:
            positions = {self._bazi_chart.year_zhu: '年柱', self._bazi_chart.month_zhu: '月柱',
                     self._bazi_chart.day_zhu: '日柱', self._bazi_chart.hour_zhu: '时柱'}

        shensha_sorted = {pos: [] for pos in positions.values()}

        for shensha in self._shensha_instances:
            positions_found, word = shensha.is_present(self._bazi_chart)
            self._log_helper.info(f"{word}\n")
            if positions_found:
                for position in positions_found:
                    shensha_info = {
                        'name': shensha.__class__.__name__,
                        'chinese_name': shensha.chinese_name,
                        'type': shensha.shensha_type,
                        'source': word,
                        'position': position
                    }
                    self._shensha_list.append(shensha_info)
                    pos_name = positions[position]
                    shensha_sorted[pos_name].append(shensha_info)

        # 记录日志
        self._log_results(shensha_sorted)

        return self._shensha_list, shensha_sorted

    def _log_results(self, shensha_sorted: Dict[str, List[Dict[str, Any]]]) -> None:
        if (self.without_time):
            zhu_name_list = ['年柱', '月柱', '日柱']
        else:
            zhu_name_list = ['年柱', '月柱', '日柱', '时柱']
        self._log_helper.info("神煞分析结果：\n")
        for pos in zhu_name_list:
            self._log_helper.info(f"{pos}：\n")
            for shensha in shensha_sorted[pos]:
                self._log_helper.info(f"神煞 {shensha['chinese_name']}，依据：{shensha['source']}\n")
            if not shensha_sorted[pos]:
                self._log_helper.info("无\n")