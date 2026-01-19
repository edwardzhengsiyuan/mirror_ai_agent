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

# bazi_core\bazi_chart.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from .property import Gan, Zhi, Shishen, Wuxing, Yinyang, Zhu, Nayin, DiShi
from lunar_python import Lunar

class BaziAnalysis(ABC):
    @abstractmethod
    def analyse(self, bazi_chart):
        pass

class BaziChartElement:
    def calculate_shishen(self, day_gan, other_gan):
        diff = (other_gan.value - day_gan.value) % 10
        if day_gan.yinyang == Yinyang.YANG:
            shishen_map = {
                0: Shishen.BIJIAN,
                1: Shishen.JIECAI,
                2: Shishen.SHISHEN,
                3: Shishen.SHANGGUAN,
                4: Shishen.PIANCAI,
                5: Shishen.ZHENGCAI,
                6: Shishen.QISHA,
                7: Shishen.ZHENGGUAN,
                8: Shishen.PIANYIN,
                9: Shishen.ZHENGYIN
            }
        else:
            shishen_map = {
                0: Shishen.BIJIAN,
                1: Shishen.SHANGGUAN,
                2: Shishen.SHISHEN,
                3: Shishen.ZHENGCAI,
                4: Shishen.PIANCAI,
                5: Shishen.ZHENGGUAN,
                6: Shishen.QISHA,
                7: Shishen.ZHENGYIN,
                8: Shishen.PIANYIN,
                9: Shishen.JIECAI
            }
        return shishen_map[diff]

class BaziChartGan(BaziChartElement):
    def __init__(self, gan: Gan, day_gan: Gan, pos: int):
        self.zhu_name = ['年','月','日','时']
        self._gan = gan
        self._name = gan.name
        self._chinese_name = gan.chinese_name
        self._yinyang = gan.yinyang.chinese_name
        self._wuxing = gan.wuxing
        self._wuxing_chinese_name = gan.wuxing.chinese_name
        if pos == 2:
            self._shishen = Shishen.RIZHU
        else:
            self._shishen = self.calculate_shishen(day_gan, gan)
        self._shishen_chinese_name = self._shishen.chinese_name
        self._pos = pos
    
    def get(self):
        return self._gan
    
    def get_shishen(self):
        return self._shishen

    def report_info(self):
        return (f'{self.zhu_name[self._pos]}干：{self._chinese_name}；阴阳：{self._yinyang}；五行：{self._wuxing_chinese_name}；十神：{self._shishen_chinese_name}\n')
    
class BaziChartZhi(BaziChartElement):
    def __init__(self, zhi: Zhi, day_gan: Gan, pos: int):
        self.zhu_name = ['年','月','日','时']
        self._zhi = zhi
        self._name = zhi.name
        self._chinese_name = zhi.chinese_name
        self._yinyang = zhi.yinyang.chinese_name
        self._wuxing = zhi.wuxing
        self._wuxing_chinese_name = zhi.wuxing.chinese_name
        self._hidden_gans = zhi.hidden_gans
        self._hidden_gans_chinese_name = [gan.chinese_name for gan in self._hidden_gans]
        self._hidden_gans_shishen_list = [self.calculate_shishen(day_gan, gan) for gan in self._hidden_gans]
        self._hidden_gans_shishen_chinese_name = [x.chinese_name for x in self._hidden_gans_shishen_list]
        self._pos = pos
    
    def get(self):
        return self._zhi
    
    def get_hidden_gans(self):
        return self._hidden_gans
    
    def get_hidden_gans_shishen_list(self):
        return self._hidden_gans_shishen_list

    def report_info(self):
        return (f'{self.zhu_name[self._pos]}支：{self._chinese_name}；阴阳：{self._yinyang}；五行：{self._wuxing_chinese_name}；藏干：{"，".join(self._hidden_gans_chinese_name)}；十神：【{"，".join(self._hidden_gans_shishen_chinese_name)}】\n')

class BaziChart:
    def __init__(self, lunar, gender, without_time = False):
        self._gender = gender  # 私有变量，使用只读属性访问
        self._lunar = lunar  # 私有变量
        self.without_time = without_time
        self.calculate_day_to_next_jie()
        self._lunar_eightchar = lunar.getEightChar()
        self._lunar_eightchar.setSect(1)
        
        # 初始化天干和地支，私有变量
        self._day_gan_init = Gan.from_chinese(self._lunar_eightchar.getDayGan())
        self._year_gan = BaziChartGan(Gan.from_chinese(self._lunar_eightchar.getYearGan()), self._day_gan_init, 0)
        self._year_zhi = BaziChartZhi(Zhi.from_chinese(self._lunar_eightchar.getYearZhi()), self._day_gan_init, 0)
        self._month_gan = BaziChartGan(Gan.from_chinese(self._lunar_eightchar.getMonthGan()), self._day_gan_init, 1)
        self._month_zhi = BaziChartZhi(Zhi.from_chinese(self._lunar_eightchar.getMonthZhi()), self._day_gan_init, 1)
        self._day_gan = BaziChartGan(Gan.from_chinese(self._lunar_eightchar.getDayGan()), self._day_gan_init, 2)
        self._day_zhi = BaziChartZhi(Zhi.from_chinese(self._lunar_eightchar.getDayZhi()), self._day_gan_init, 2)
        self.taiyuan = self._lunar_eightchar.getTaiYuan()
        self.minggong = self._lunar_eightchar.getMingGong()
        self.shengong = self._lunar_eightchar.getShenGong()
        self._taiyuan_gan = BaziChartGan(Gan.from_chinese(self.taiyuan[0]), self._day_gan_init, 4)
        self._taiyuan_zhi = BaziChartZhi(Zhi.from_chinese(self.taiyuan[1]), self._day_gan_init, 4)
        self._minggong_gan = BaziChartGan(Gan.from_chinese(self.minggong[0]), self._day_gan_init, 5)
        self._minggong_zhi = BaziChartZhi(Zhi.from_chinese(self.minggong[1]), self._day_gan_init, 5)
        self._shengong_gan = BaziChartGan(Gan.from_chinese(self.shengong[0]), self._day_gan_init, 6)
        self._shengong_zhi = BaziChartZhi(Zhi.from_chinese(self.shengong[1]), self._day_gan_init, 6)

        # 初始化柱，私有变量
        self._year_zhu = Zhu(self._year_gan, self._year_zhi)
        self._month_zhu = Zhu(self._month_gan, self._month_zhi)
        self._day_zhu = Zhu(self._day_gan, self._day_zhi)

        self._taiyuan_zhu = Zhu(self._taiyuan_gan, self._taiyuan_zhi)
        self._minggong_zhu = Zhu(self._minggong_gan, self._minggong_zhi)
        self._shengong_zhu = Zhu(self._shengong_gan, self._shengong_zhi)

        self._tai_ming_shen_zhu_list = [self._taiyuan_zhu, self._minggong_zhu, self._shengong_zhu]

        # 计算十神，私有变量
        self._year_gan_shishen = self._year_gan.get_shishen()
        self._month_gan_shishen = self._month_gan.get_shishen()
        self._day_gan_shishen = self._day_gan.get_shishen()

        # 藏干，私有变量
        self._year_zhi_hidden_gans = self._year_zhi.get_hidden_gans()
        self._month_zhi_hidden_gans = self._month_zhi.get_hidden_gans()
        self._day_zhi_hidden_gans = self._day_zhi.get_hidden_gans()

        # 藏干十神，私有变量
        self._year_zhi_hidden_gans_shishen = self._year_zhi.get_hidden_gans_shishen_list()
        self._month_zhi_hidden_gans_shishen = self._month_zhi.get_hidden_gans_shishen_list()
        self._day_zhi_hidden_gans_shishen = self._day_zhi.get_hidden_gans_shishen_list()

        # 纳音与地势：统一在本项目内计算，避免第三方库在 Windows 环境下的编码差异
        self.year_nayin = self._calc_nayin(self._year_gan._gan, self._year_zhi._zhi)
        self.month_nayin = self._calc_nayin(self._month_gan._gan, self._month_zhi._zhi)
        self.day_nayin = self._calc_nayin(self._day_gan._gan, self._day_zhi._zhi)

        # 地势有两套口径：
        # 1) 日主在四支的地势（用于 daygan_dishi）：以“日干”为基准，分别看年/月/日/时支的十二长生
        # 2) 单柱自坐地势（用于 zizuo_dishi）：以“该柱天干”为基准，看该柱地支的十二长生
        self.year_dishi = self._calc_dishi(self._day_gan._gan, self._year_zhi._zhi)
        self.month_dishi = self._calc_dishi(self._day_gan._gan, self._month_zhi._zhi)
        self.day_dishi = self._calc_dishi(self._day_gan._gan, self._day_zhi._zhi)

        self.year_zizuo_dishi = self._calc_dishi(self._year_gan._gan, self._year_zhi._zhi)
        self.month_zizuo_dishi = self._calc_dishi(self._month_gan._gan, self._month_zhi._zhi)
        self.day_zizuo_dishi = self._calc_dishi(self._day_gan._gan, self._day_zhi._zhi)
        # 列表，私有变量
        if not (without_time):
            self._hour_gan = BaziChartGan(Gan.from_chinese(self._lunar_eightchar.getTimeGan()), self._day_gan_init, 3)
            self._hour_zhi = BaziChartZhi(Zhi.from_chinese(self._lunar_eightchar.getTimeZhi()), self._day_gan_init, 3)
            self._hour_zhu = Zhu(self._hour_gan, self._hour_zhi)
            self._gan_list = [self._year_gan, self._month_gan, self._day_gan, self._hour_gan]
            self._zhi_list = [self._year_zhi, self._month_zhi, self._day_zhi, self._hour_zhi]
            self._zhu_list = [self._year_zhu, self._month_zhu, self._day_zhu, self._hour_zhu]
            self._hour_gan_shishen = self._hour_gan.get_shishen()
            self._hour_zhi_hidden_gans = self._hour_zhi.get_hidden_gans()
            self._zhi_hidden_gans_list = [
                self._year_zhi_hidden_gans,
                self._month_zhi_hidden_gans,
                self._day_zhi_hidden_gans,
                self._hour_zhi_hidden_gans
            ]
            self._hour_zhi_hidden_gans_shishen = self._hour_zhi.get_hidden_gans_shishen_list()
            self._gan_shishen_list = [self._year_gan_shishen, self._month_gan_shishen,self._day_gan_shishen,self._hour_gan_shishen]
            self._zhi_hidden_gans_shishen_list = [self._year_zhi_hidden_gans_shishen, self._month_zhi_hidden_gans_shishen, self._day_zhi_hidden_gans_shishen, self._hour_zhi_hidden_gans_shishen]
            self.hour_nayin = self._calc_nayin(self._hour_gan._gan, self._hour_zhi._zhi)
            self.hour_dishi = self._calc_dishi(self._day_gan._gan, self._hour_zhi._zhi)
            self.nayin_list = [self.year_nayin, self.month_nayin, self.day_nayin, self.hour_nayin]
            self.dishi_list = [self.year_dishi, self.month_dishi, self.day_dishi, self.hour_dishi]
            self.hour_zizuo_dishi = self._calc_dishi(self._hour_gan._gan, self._hour_zhi._zhi)
            self.dishi_zizuo_list = [self.year_zizuo_dishi, self.month_zizuo_dishi, self.day_zizuo_dishi, self.hour_zizuo_dishi]
            self.xunkong_list = [
                self._parse_xunkong_to_zhis(self._lunar.getYearXunKongExact()),
                self._parse_xunkong_to_zhis(self._lunar.getMonthXunKongExact()),
                self._parse_xunkong_to_zhis(self._lunar.getDayXunKongExact()),
                self._parse_xunkong_to_zhis(self._lunar.getTimeXunKong()),
            ]
        else:
            self._gan_list = [self._year_gan, self._month_gan, self._day_gan]
            self._zhi_list = [self._year_zhi, self._month_zhi, self._day_zhi]
            self._zhu_list = [self._year_zhu, self._month_zhu, self._day_zhu]
            self._zhi_hidden_gans_list = [
                self._year_zhi_hidden_gans,
                self._month_zhi_hidden_gans,
                self._day_zhi_hidden_gans
            ]
            self._gan_shishen_list = [self._year_gan_shishen, self._month_gan_shishen,self._day_gan_shishen]
            self._zhi_hidden_gans_shishen_list = [self._year_zhi_hidden_gans_shishen, self._month_zhi_hidden_gans_shishen, self._day_zhi_hidden_gans_shishen]
            self.nayin_list = [self.year_nayin, self.month_nayin, self.day_nayin]
            self.dishi_list = [self.year_dishi, self.month_dishi, self.day_dishi]
            self.dishi_zizuo_list = [self.year_zizuo_dishi, self.month_zizuo_dishi, self.day_zizuo_dishi]
            self.xunkong_list = [
                self._parse_xunkong_to_zhis(self._lunar.getYearXunKongExact()),
                self._parse_xunkong_to_zhis(self._lunar.getMonthXunKongExact()),
                self._parse_xunkong_to_zhis(self._lunar.getDayXunKongExact()),
            ]
        self.is_special = False
        self.refer = None
        
        # 创建基于当前日干的十神缓存，用于大运流年流月计算加速
        self.create_shishen_cache_for_current_day_gan()
        
        self.calculate_dayun_liunian()
        self.calculate_peiou_fangwei_by_swh()

    def calculate_shishen(self, day_gan, other_gan):
        diff = (other_gan.value - day_gan.value) % 10
        if day_gan.yinyang == Yinyang.YANG:
            shishen_map = {
                0: Shishen.BIJIAN,
                1: Shishen.JIECAI,
                2: Shishen.SHISHEN,
                3: Shishen.SHANGGUAN,
                4: Shishen.PIANCAI,
                5: Shishen.ZHENGCAI,
                6: Shishen.QISHA,
                7: Shishen.ZHENGGUAN,
                8: Shishen.PIANYIN,
                9: Shishen.ZHENGYIN
            }
        else:
            shishen_map = {
                0: Shishen.BIJIAN,
                1: Shishen.SHANGGUAN,
                2: Shishen.SHISHEN,
                3: Shishen.ZHENGCAI,
                4: Shishen.PIANCAI,
                5: Shishen.ZHENGGUAN,
                6: Shishen.QISHA,
                7: Shishen.ZHENGYIN,
                8: Shishen.PIANYIN,
                9: Shishen.JIECAI
            }
        return shishen_map[diff]
    
    def check_dishi(self, zhu: Zhu):
        return self._calc_dishi(zhu.gan._gan, zhu.zhi._zhi)

    def _calc_dishi(self, gan: Gan, zhi: Zhi) -> DiShi:
        CHANG_SHENG = (
            DiShi.CHANGSHENG,
            DiShi.MUYU,
            DiShi.GUANDAI,
            DiShi.LINGUAN,
            DiShi.DIWANG,
            DiShi.SHUAI,
            DiShi.BING,
            DiShi.SI,
            DiShi.MU,
            DiShi.JUE,
            DiShi.TAI,
            DiShi.YANG,
        )

        CHANG_SHENG_OFFSET = {
            "甲": 1,
            "丙": 10,
            "戊": 10,
            "庚": 7,
            "壬": 4,
            "乙": 6,
            "丁": 9,
            "己": 9,
            "辛": 0,
            "癸": 3
        }
        index = (CHANG_SHENG_OFFSET.get(gan.chinese_name) + (zhi.value if gan.value % 2 == 0 else -zhi.value)) % 12

        return CHANG_SHENG[index]
    
    def create_shishen_cache_for_current_day_gan(self):
        """
        为当前日干创建十神缓存
        """
        if hasattr(self, '_shishen_cache'):
            return  # 缓存已存在
            
        # print(f"为日干{self.day_gan._gan.chinese_name}创建十神缓存...")
        
        # 所有天干和地支
        all_gans = [Gan.JIA, Gan.YI, Gan.BING, Gan.DING, Gan.WU, 
                    Gan.JI, Gan.GENG, Gan.XIN, Gan.REN, Gan.GUI]
        all_zhis = [Zhi.ZI, Zhi.CHOU, Zhi.YIN, Zhi.MAO, Zhi.CHEN, Zhi.SI,
                    Zhi.WU, Zhi.WEI, Zhi.SHEN, Zhi.YOU, Zhi.XU, Zhi.HAI]
        
        self._shishen_cache = {"gan_shishen": {}, "zhi_shishen": {}}
        
        # 计算当前日干与所有天干的十神关系
        for gan in all_gans:
            gan_name = gan.chinese_name
            shishen = self.calculate_shishen(self.day_gan._gan, gan)
            self._shishen_cache["gan_shishen"][gan_name] = shishen
        
        # 计算当前日干与所有地支藏干的十神关系
        for zhi in all_zhis:
            zhi_name = zhi.chinese_name
            # 使用地支的主藏干计算十神
            main_hidden_gan = zhi.hidden_gans[0]
            shishen = self.calculate_shishen(self.day_gan._gan, main_hidden_gan)
            self._shishen_cache["zhi_shishen"][zhi_name] = shishen
        
        # print(f"十神缓存创建完成，包含{len(self._shishen_cache['gan_shishen'])}个天干和{len(self._shishen_cache['zhi_shishen'])}个天干和{len(self._shishen_cache['zhi_shishen'])}个地支关系")
    
    def get_cached_shishen(self, ganzhi_name, is_gan=True):
        """
        从缓存中获取十神
        
        Args:
            ganzhi_name (str): 天干或地支名称
            is_gan (bool): True表示天干，False表示地支
        
        Returns:
            Shishen: 十神枚举
        """
        if not hasattr(self, '_shishen_cache'):
            self.create_shishen_cache_for_current_day_gan()
        
        if is_gan:
            return self._shishen_cache["gan_shishen"].get(ganzhi_name)
        else:
            return self._shishen_cache["zhi_shishen"].get(ganzhi_name)

    def generate_ganzhi_and_shishen_for_yun_nian(self, target, ganzhi, gan_list_rear = None, zhi_list_rear = None):
        gan = Gan.from_chinese(ganzhi[0])
        zhi = Zhi.from_chinese(ganzhi[1])
        target["gan"] = gan.name
        target["zhi"] = zhi.name
        target["gan_wuxing"] = gan.wuxing.name
        target["zhi_wuxing"] = zhi.wuxing.name
        
        # 使用缓存获取十神，避免重复计算
        target["gan_shishen"] = self.get_cached_shishen(ganzhi[0], is_gan=True).name
        target["zhi_shishen"] = self.get_cached_shishen(ganzhi[1], is_gan=False).name
        
        if gan_list_rear:
            target["gan_relation"] = gan.get_wuhe_relations_enum(gan_list_rear)
            target["zhi_relation"] = zhi.get_relations_enum(zhi_list_rear)

    @staticmethod
    def _calc_nayin(gan: Gan, zhi: Zhi) -> Nayin:
        """
        通过干支计算纳音（60甲子 -> 30纳音）。
        采用枚举对枚举映射，避免中文字符串编码差异。
        """
        mapping: dict[tuple[Gan, Zhi], Nayin] = {
            (Gan.JIA, Zhi.ZI): Nayin.HAI_ZHONG_JIN,
            (Gan.YI, Zhi.CHOU): Nayin.HAI_ZHONG_JIN,
            (Gan.BING, Zhi.YIN): Nayin.LU_ZHONG_HUO,
            (Gan.DING, Zhi.MAO): Nayin.LU_ZHONG_HUO,
            (Gan.WU, Zhi.CHEN): Nayin.DA_LIN_MU,
            (Gan.JI, Zhi.SI): Nayin.DA_LIN_MU,
            (Gan.GENG, Zhi.WU): Nayin.LU_PANG_TU,
            (Gan.XIN, Zhi.WEI): Nayin.LU_PANG_TU,
            (Gan.REN, Zhi.SHEN): Nayin.JIAN_FENG_JIN,
            (Gan.GUI, Zhi.YOU): Nayin.JIAN_FENG_JIN,
            (Gan.JIA, Zhi.XU): Nayin.SHAN_TOU_HUO,
            (Gan.YI, Zhi.HAI): Nayin.SHAN_TOU_HUO,
            (Gan.BING, Zhi.ZI): Nayin.JIAN_XIA_SHUI,
            (Gan.DING, Zhi.CHOU): Nayin.JIAN_XIA_SHUI,
            (Gan.WU, Zhi.YIN): Nayin.CHENG_TOU_TU,
            (Gan.JI, Zhi.MAO): Nayin.CHENG_TOU_TU,
            (Gan.GENG, Zhi.CHEN): Nayin.BAI_LA_JIN,
            (Gan.XIN, Zhi.SI): Nayin.BAI_LA_JIN,
            (Gan.REN, Zhi.WU): Nayin.YANG_LIU_MU,
            (Gan.GUI, Zhi.WEI): Nayin.YANG_LIU_MU,
            (Gan.JIA, Zhi.SHEN): Nayin.QUAN_ZHONG_SHUI,
            (Gan.YI, Zhi.YOU): Nayin.QUAN_ZHONG_SHUI,
            (Gan.BING, Zhi.XU): Nayin.WU_SHANG_TU,
            (Gan.DING, Zhi.HAI): Nayin.WU_SHANG_TU,
            (Gan.WU, Zhi.ZI): Nayin.PI_LI_HUO,
            (Gan.JI, Zhi.CHOU): Nayin.PI_LI_HUO,
            (Gan.GENG, Zhi.YIN): Nayin.SONG_BAI_MU,
            (Gan.XIN, Zhi.MAO): Nayin.SONG_BAI_MU,
            (Gan.REN, Zhi.CHEN): Nayin.CHANG_LIU_SHUI,
            (Gan.GUI, Zhi.SI): Nayin.CHANG_LIU_SHUI,
            (Gan.JIA, Zhi.WU): Nayin.SHA_ZHONG_JIN,
            (Gan.YI, Zhi.WEI): Nayin.SHA_ZHONG_JIN,
            (Gan.BING, Zhi.SHEN): Nayin.SHAN_XIA_HUO,
            (Gan.DING, Zhi.YOU): Nayin.SHAN_XIA_HUO,
            (Gan.WU, Zhi.XU): Nayin.PING_DI_MU,
            (Gan.JI, Zhi.HAI): Nayin.PING_DI_MU,
            (Gan.GENG, Zhi.ZI): Nayin.BI_SHANG_TU,
            (Gan.XIN, Zhi.CHOU): Nayin.BI_SHANG_TU,
            (Gan.REN, Zhi.YIN): Nayin.JIN_BO_JIN,
            (Gan.GUI, Zhi.MAO): Nayin.JIN_BO_JIN,
            (Gan.JIA, Zhi.CHEN): Nayin.FO_DENG_HUO,
            (Gan.YI, Zhi.SI): Nayin.FO_DENG_HUO,
            (Gan.BING, Zhi.WU): Nayin.TIAN_HE_SHUI,
            (Gan.DING, Zhi.WEI): Nayin.TIAN_HE_SHUI,
            (Gan.WU, Zhi.SHEN): Nayin.DA_YI_TU,
            (Gan.JI, Zhi.YOU): Nayin.DA_YI_TU,
            (Gan.GENG, Zhi.XU): Nayin.CHAI_CHUAN_JIN,
            (Gan.XIN, Zhi.HAI): Nayin.CHAI_CHUAN_JIN,
            (Gan.REN, Zhi.ZI): Nayin.SANG_ZHE_MU,
            (Gan.GUI, Zhi.CHOU): Nayin.SANG_ZHE_MU,
            (Gan.JIA, Zhi.YIN): Nayin.DA_XI_SHUI,
            (Gan.YI, Zhi.MAO): Nayin.DA_XI_SHUI,
            (Gan.BING, Zhi.CHEN): Nayin.SHA_ZHONG_TU,
            (Gan.DING, Zhi.SI): Nayin.SHA_ZHONG_TU,
            (Gan.WU, Zhi.WU): Nayin.TIAN_SHANG_HUO,
            (Gan.JI, Zhi.WEI): Nayin.TIAN_SHANG_HUO,
            (Gan.GENG, Zhi.SHEN): Nayin.SHI_LIU_MU,
            (Gan.XIN, Zhi.YOU): Nayin.SHI_LIU_MU,
            (Gan.REN, Zhi.XU): Nayin.DA_HAI_SHUI,
            (Gan.GUI, Zhi.HAI): Nayin.DA_HAI_SHUI,
        }
        try:
            return mapping[(gan, zhi)]
        except KeyError as e:
            raise ValueError(f"Unsupported ganzhi for Nayin: {gan.name}{zhi.name}") from e

    @staticmethod
    def _parse_xunkong_to_zhis(xunkong: str) -> tuple[Zhi, Zhi]:
        # e.g. "子丑空" / "子丑" / " 子丑 空 "
        cleaned = xunkong.replace("空", "").strip()
        if len(cleaned) != 2:
            raise ValueError(f"Invalid xunkong value: {xunkong!r}")
        return (Zhi.from_chinese(cleaned[0]), Zhi.from_chinese(cleaned[1]))

    def calculate_dayun_liunian(self, use_cache=True):
        """
        计算大运流年流月，支持使用缓存加速
        
        Args:
            use_cache (bool): 是否使用缓存，默认True
        """
        # 加载流年流月缓存（只在第一次调用时加载）
        if not hasattr(self, '_liunian_liuyue_cache') and use_cache:
            try:
                import os
                if os.path.exists("efficient_liunian_liuyue_cache.json"):
                    import json
                    with open("efficient_liunian_liuyue_cache.json", 'r', encoding='utf-8') as f:
                        self._liunian_liuyue_cache = json.load(f)
                    # print("已加载流年流月缓存")
                else:
                    # print("流年流月缓存文件不存在")
                    self._liunian_liuyue_cache = None
            except Exception as e:
                # print(f"流年流月缓存加载失败: {e}")
                self._liunian_liuyue_cache = None
        
        # 使用已加载的流年流月缓存
        liunian_liuyue_cache = getattr(self, '_liunian_liuyue_cache', None) if use_cache else None
        
        self.yun = self._lunar_eightchar.getYun(1 if self._gender == "male" else 0, 2)
        self.start_yun = [self.yun.getStartYear(), self.yun.getStartMonth(), self.yun.getStartDay(), self.yun.getStartHour()]
        self.dayun = self.yun.getDaYun()
        res = []
        self.dayun_liunian_liuyue_frontend_res = []
        for dayun in self.dayun:
            gan_list_rear = [x._gan for x in self.gan_list]
            zhi_list_rear = [x._zhi for x in self.zhi_list]
            dayun_res = dict()
            if dayun.getIndex() > 0:
                ganzhi = dayun.getGanZhi()
                self.generate_ganzhi_and_shishen_for_yun_nian(dayun_res, ganzhi, gan_list_rear, zhi_list_rear)
                gan_list_rear.append(Gan.from_chinese(ganzhi[0]))
                zhi_list_rear.append(Zhi.from_chinese(ganzhi[1]))
            dayun_word = f"第{dayun.getIndex()}步运{dayun.getGanZhi()}【{dayun_res['gan_shishen']}{dayun_res['zhi_shishen']}】：" if dayun.getIndex() > 0 else "起运前"
            dayun_res["age"] = dayun.getStartAge()
            dayun_res["year"] = dayun.getStartYear()
            dayun_res["liunian"] = []
            res.append(dayun_word)
            for liunian in dayun.getLiuNian():
                liunian_res = dict()
                
                # 使用流年流月缓存获取天干地支
                if liunian_liuyue_cache and str(liunian.getYear()) in liunian_liuyue_cache["liunian"]:
                    cached_liunian = liunian_liuyue_cache["liunian"][str(liunian.getYear())]
                    ganzhi = cached_liunian["ganzhi"]
                else:
                    ganzhi = liunian.getGanZhi()
                
                self.generate_ganzhi_and_shishen_for_yun_nian(liunian_res, ganzhi, gan_list_rear, zhi_list_rear)
                liunian_res["age"] = liunian.getAge()
                liunian_res["year"] = liunian.getYear()
                liunian_word = f"{liunian.getYear()}{ganzhi}【{liunian_res['gan_shishen']}{liunian_res['zhi_shishen']}】{liunian.getAge()}岁："

                liunian_res["liuyue"] = []
                liunina_lunar = Lunar.fromYmd(liunian_res["year"],6,1)
                jieqi = liunina_lunar.getJieQiTable()
                jie_name_list = ["立春", "惊蛰", "清明", "立夏", "芒种", "小暑", "立秋", "白露", "寒露", "立冬", "大雪", "小寒"]
                liuyue_list = liunian.getLiuYue()
                gan_list_rear.append(Gan.from_chinese(ganzhi[0]))
                zhi_list_rear.append(Zhi.from_chinese(ganzhi[1]))
                for i in range(12):
                    liuyue_res = dict()
                    
                    # 使用流年流月缓存获取流月天干地支
                    if liunian_liuyue_cache and str(liunian_res["year"]) in liunian_liuyue_cache["liuyue"]:
                        year_liuyue_cache = liunian_liuyue_cache["liuyue"][str(liunian_res["year"])]
                        month_key = f"{i+1:02d}"
                        if month_key in year_liuyue_cache:
                            cached_liuyue = year_liuyue_cache[month_key]
                            ganzhi = cached_liuyue["ganzhi"]
                        else:
                            ganzhi = liuyue_list[i].getGanZhi()
                    else:
                        ganzhi = liuyue_list[i].getGanZhi()
                    
                    jie_time = jieqi[jie_name_list[i]]
                    liuyue_res["month"] = jie_time.getMonth()
                    liuyue_res["day"] = jie_time.getDay()
                    self.generate_ganzhi_and_shishen_for_yun_nian(liuyue_res, ganzhi, gan_list_rear, zhi_list_rear)
                    liunian_res["liuyue"].append(liuyue_res)
                gan_list_rear.pop()
                zhi_list_rear.pop()
                dayun_res["liunian"].append(liunian_res)
                res.append(liunian_word)
            self.dayun_liunian_liuyue_frontend_res.append(dayun_res)
        return res

    def calculate_day_to_next_jie(self):
        # 示例方法，根据节气计算季节
        next_jie = self._lunar.getNextJie(False)
        jieqi_table = self._lunar.getJieQiTable()
        jie_solar = jieqi_table[next_jie.getName()]
        self_solar = self._lunar.getSolar()
        distance_by_minute = jie_solar.subtractMinute(self_solar)
        distance_by_day = distance_by_minute / (60 * 24)
        self._is_second_half_of_month = distance_by_day < 15
        self._is_ji_yue = distance_by_day < 18 and next_jie.getName() in ("立春", "立夏", "立秋", "立冬")

    def get_zhi_by_index(self, index):
        if index == 0:
            return self._year_zhi
        elif index == 1:
            return self._month_zhi
        elif index == 2:
            return self._day_zhi
        elif index == 3 and not self.without_time:
            return self._hour_zhi
        else:
            raise IndexError("Invalid index")

    def assign_shishen_to_hidden_gans(self, hidden_gans):
        return [self.calculate_shishen(self._day_gan, gan) for gan in hidden_gans]
    
    def get_all_shishen_in_zhu_by_index(self, index):
        """
        返回指定柱的所有十神，包括天干的十神和地支藏干的十神。
        """
        gan_shishen = self._gan_shishen_list[index][1]  # 只需要十神
        zhi_hidden_gans_shishen = self._zhi_hidden_gans_shishen_list[index]
        return [gan_shishen] + zhi_hidden_gans_shishen

    def detailed_info(self):
        """
        返回八字的详细信息，包括天干、地支和藏干的十神
        """
        res = []
        for gan in self._gan_list:
            res.append(gan.report_info())
        for zhi in self._zhi_list:
            res.append(zhi.report_info())
        return res

    def calculate_peiou_fangwei_by_swh(self):
        zhi_num = (self.month_zhi._zhi.value + self._lunar.getDay() - 1) % 12
        peiou_fangwei_list = ["北方对南方", "东北方对西南方", "东北方对西南方", "东方对西方", "东南方对西北方", "东南方对西北方", "北方对南方", "东北方对西南方", "东北方对西南方", "东方对西方", "东南方对西北方", "东南方对西北方"]
        self.peiou_fangwei = peiou_fangwei_list[zhi_num]

    def __str__(self):
        return f"{self._year_zhu.chinese_name} {self._month_zhu.chinese_name} {self._day_zhu.chinese_name} {self._hour_zhu.chinese_name}"
    
    # 以下是添加的属性方法

    @property
    def lunar(self):
        return self._lunar

    @property
    def lunar_eightchar(self):
        return self._lunar_eightchar

    @property
    def gender(self) -> str:
        return self._gender

    @property
    def year_gan(self):
        return self._year_gan

    @property
    def month_gan(self):
        return self._month_gan

    @property
    def day_gan(self):
        return self._day_gan

    @property
    def hour_gan(self):
        return self._hour_gan if not self.without_time else None

    @property
    def year_zhi(self):
        return self._year_zhi

    @property
    def month_zhi(self):
        return self._month_zhi

    @property
    def day_zhi(self):
        return self._day_zhi

    @property
    def hour_zhi(self):
        return self._hour_zhi if not self.without_time else None

    @property
    def year_zhu(self) -> Zhu:
        return self._year_zhu

    @property
    def month_zhu(self) -> Zhu:
        return self._month_zhu

    @property
    def day_zhu(self) -> Zhu:
        return self._day_zhu

    @property
    def hour_zhu(self) -> Zhu:
        return self._hour_zhu if not self.without_time else None

    @property
    def gan_list(self) -> List[BaziChartGan]:
        return self._gan_list

    @property
    def zhi_list(self) -> List[BaziChartZhi]:
        return self._zhi_list

    @property
    def zhu_list(self) -> List[Zhu]:
        return self._zhu_list

    @property
    def year_gan_shishen(self):
        return self._year_gan_shishen

    @property
    def month_gan_shishen(self):
        return self._month_gan_shishen

    @property
    def day_gan_shishen(self):
        return self._day_gan_shishen

    @property
    def hour_gan_shishen(self):
        return self._hour_gan_shishen if not self.without_time else None

    @property
    def year_zhi_hidden_gans(self):
        return self._year_zhi_hidden_gans

    @property
    def month_zhi_hidden_gans(self):
        return self._month_zhi_hidden_gans

    @property
    def day_zhi_hidden_gans(self):
        return self._day_zhi_hidden_gans

    @property
    def hour_zhi_hidden_gans(self):
        return self._hour_zhi_hidden_gans if not self.without_time else None

    @property
    def zhi_hidden_gans_list(self) -> List[List[Gan]]:
        return self._zhi_hidden_gans_list

    @property
    def year_zhi_hidden_gans_shishen(self):
        return self._year_zhi_hidden_gans_shishen

    @property
    def month_zhi_hidden_gans_shishen(self):
        return self._month_zhi_hidden_gans_shishen

    @property
    def day_zhi_hidden_gans_shishen(self):
        return self._day_zhi_hidden_gans_shishen

    @property
    def hour_zhi_hidden_gans_shishen(self):
        return self._hour_zhi_hidden_gans_shishen if not self.without_time else None

    @property
    def gan_shishen_list(self) -> List[tuple]:
        return self._gan_shishen_list

    @property
    def zhi_hidden_gans_shishen_list(self) -> List[List[Shishen]]:
        return self._zhi_hidden_gans_shishen_list

    @property
    def is_second_half_of_month(self) -> bool:
        return self._is_second_half_of_month

    @property
    def is_ji_yue(self) -> bool:
        return self._is_ji_yue
