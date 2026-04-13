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

import time
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
from ...core import Gan, Zhi
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
        # 记录神煞分析开始时间
        shensha_start_time = time.time()
        
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
        
        # 记录神煞分析结束时间并计算耗时
        shensha_end_time = time.time()
        shensha_time = shensha_end_time - shensha_start_time
        self._log_helper.info(f"神煞分析耗时: {shensha_time:.4f} 秒\n")

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

    def analyse_date(self, year: int, month: int, day: int, hour: int = 12) -> Dict[str, List[Dict[str, Any]]]:
        """
        分析指定日期的神煞（包含大运、流年、流月、流日、流时）
        """
        from lunar_python import Solar
        
        # 1. 计算指定日期的四柱（流年、流月、流日、流时）
        solar = Solar.fromYmdHms(year, month, day, hour, 0, 0)
        lunar = solar.getLunar()
        
        # 获取天干地支字符串，转换为Gan和Zhi对象
        # 注意：lunar-python返回的是简体中文，可以直接使用Gan.from_chinese
        
        # 流年
        liunian_gan = Gan.from_chinese(lunar.getYearGan())
        liunian_zhi = Zhi.from_chinese(lunar.getYearZhi())
        
        # 流月
        liuyue_gan = Gan.from_chinese(lunar.getMonthGan())
        liuyue_zhi = Zhi.from_chinese(lunar.getMonthZhi())
        
        # 流日
        liuri_gan = Gan.from_chinese(lunar.getDayGan())
        liuri_zhi = Zhi.from_chinese(lunar.getDayZhi())
        
        # 流时
        liushi_gan = Gan.from_chinese(lunar.getTimeGan())
        liushi_zhi = Zhi.from_chinese(lunar.getTimeZhi())
        
        date_ganzhi = {
            'liunian': (liunian_gan, liunian_zhi),
            'liuyue': (liuyue_gan, liuyue_zhi),
            'liuri': (liuri_gan, liuri_zhi),
            'liushi': (liushi_gan, liushi_zhi)
        }
        
        # 2. 计算当前大运
        current_dayun = None
        if hasattr(self._bazi_chart, 'dayun'):
            for i, dayun in enumerate(self._bazi_chart.dayun):
                start_year = dayun.getStartYear()
                end_year = dayun.getEndYear()
                
                # Check if this year is within range
                if start_year <= year < end_year:
                    current_dayun = dayun
                    break
        
        if current_dayun and current_dayun.getIndex() > 0:
            ganzhi = current_dayun.getGanZhi()
            if len(ganzhi) >= 2:
                 date_ganzhi['dayun'] = (Gan.from_chinese(ganzhi[0]), Zhi.from_chinese(ganzhi[1]))

        # 3. 分析神煞
        result = {}
        for pillar_name, (gan, zhi) in date_ganzhi.items():
            result[pillar_name] = []
            for shensha in self._shensha_instances:
                # 检查该神煞是否存在于该柱
                if shensha.is_present_in_zhu(gan, zhi, self._bazi_chart):
                    shensha_info = {
                        'name': shensha.__class__.__name__,
                        'chinese_name': shensha.chinese_name,
                        'type': shensha.shensha_type,
                        'gan': gan.chinese_name,
                        'zhi': zhi.chinese_name,
                        'pillar': pillar_name
                    }
                    result[pillar_name].append(shensha_info)
                    
        return result

    def analyse_compatibility(self, other_chart: BaziChart) -> Dict[str, List[Dict[str, Any]]]:
        """
        分析两个命盘的互看神煞（合盘）
        
        Args:
            other_chart (BaziChart): 对方的命盘 (Chart B)
            
        Returns:
            Dict[str, List[Dict[str, Any]]]:
                'a_has_b_shensha': Chart A 的柱子中，有哪些是 Chart B 的神煞（A 满足 B 的规则，即 A 旺 B）
                'b_has_a_shensha': Chart B 的柱子中，有哪些是 Chart A 的神煞（B 满足 A 的规则，即 B 旺 A）
        """
        result = {
            'a_has_b_shensha': [],
            'b_has_a_shensha': []
        }
        
        # 准备 Pillar Mapping
        def get_pillar_name(index):
            names = ['年柱', '月柱', '日柱', '时柱']
            if 0 <= index < len(names):
                return names[index]
            return f"柱{index}"

        # 德秀贵人合盘：用 is_present(己方, 对方) 去对方盘里找贵人，返回对方盘中带德/秀的柱
        dexiu_positions_a_has_b = []
        dexiu_positions_b_has_a = []
        for s in self._shensha_instances:
            if isinstance(s, DexiuGuiren):
                dexiu_positions_a_has_b, _ = s.is_present(other_chart, self._bazi_chart)   # B 的规则，在 A 里找
                dexiu_positions_b_has_a, _ = s.is_present(self._bazi_chart, other_chart)   # A 的规则，在 B 里找
                break

        # 1. 检查 A 中有哪些 B 的神煞 (Context: B, Target: A)
        # "命盘A中有哪些命盘B中的神煞" -> A 旺 B
        for i, zhu in enumerate(self._bazi_chart.zhu_list):
            gan = zhu.gan._gan
            zhi = zhu.zhi._zhi
            pillar_name = get_pillar_name(i)
            for shensha in self._shensha_instances:
                if isinstance(shensha, DexiuGuiren):
                    if zhu in dexiu_positions_a_has_b:
                        info = {
                            'name': shensha.__class__.__name__,
                            'chinese_name': shensha.chinese_name,
                            'type': shensha.shensha_type,
                            'gan': gan.chinese_name,
                            'zhi': zhi.chinese_name,
                            'pillar': pillar_name,
                            'description': f"命盘A的{pillar_name}({gan.chinese_name}{zhi.chinese_name})是命盘B的{shensha.chinese_name}"
                        }
                        result['a_has_b_shensha'].append(info)
                elif shensha.is_present_in_zhu(gan, zhi, other_chart):
                    info = {
                        'name': shensha.__class__.__name__,
                        'chinese_name': shensha.chinese_name,
                        'type': shensha.shensha_type,
                        'gan': gan.chinese_name,
                        'zhi': zhi.chinese_name,
                        'pillar': pillar_name,
                        'description': f"命盘A的{pillar_name}({gan.chinese_name}{zhi.chinese_name})是命盘B的{shensha.chinese_name}"
                    }
                    result['a_has_b_shensha'].append(info)

        # 2. 检查 B 中有哪些 A 的神煞 (Context: A, Target: B)
        # "命盘B中有哪些盘A中的神煞" -> B 旺 A
        for i, zhu in enumerate(other_chart.zhu_list):
            gan = zhu.gan._gan
            zhi = zhu.zhi._zhi
            pillar_name = get_pillar_name(i)
            for shensha in self._shensha_instances:
                if isinstance(shensha, DexiuGuiren):
                    if zhu in dexiu_positions_b_has_a:
                        info = {
                            'name': shensha.__class__.__name__,
                            'chinese_name': shensha.chinese_name,
                            'type': shensha.shensha_type,
                            'gan': gan.chinese_name,
                            'zhi': zhi.chinese_name,
                            'pillar': pillar_name,
                            'description': f"命盘B的{pillar_name}({gan.chinese_name}{zhi.chinese_name})是命盘A的{shensha.chinese_name}"
                        }
                        result['b_has_a_shensha'].append(info)
                elif shensha.is_present_in_zhu(gan, zhi, self._bazi_chart):
                    info = {
                        'name': shensha.__class__.__name__,
                        'chinese_name': shensha.chinese_name,
                        'type': shensha.shensha_type,
                        'gan': gan.chinese_name,
                        'zhi': zhi.chinese_name,
                        'pillar': pillar_name,
                        'description': f"命盘B的{pillar_name}({gan.chinese_name}{zhi.chinese_name})是命盘A的{shensha.chinese_name}"
                    }
                    result['b_has_a_shensha'].append(info)
                    
        return result