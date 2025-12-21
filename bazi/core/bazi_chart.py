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
from .property import Gan, Zhi, Shishen, Wuxing, Yinyang, Zhu
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

        self.year_nayin = self._lunar_eightchar.getYearNaYin()
        self.month_nayin = self._lunar_eightchar.getMonthNaYin()
        self.day_nayin = self._lunar_eightchar.getDayNaYin()
        self.year_dishi = self._lunar_eightchar.getYearDiShi()
        self.month_dishi = self._lunar_eightchar.getMonthDiShi()
        self.day_dishi = self._lunar_eightchar.getDayDiShi()

        self.year_zizuo_dishi = self.check_dishi(self.year_zhu)
        self.month_zizuo_dishi = self.check_dishi(self.month_zhu)
        self.day_zizuo_dishi = self.check_dishi(self.day_zhu)
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
            self.hour_nayin = self._lunar_eightchar.getTimeNaYin()
            self.hour_dishi = self._lunar_eightchar.getTimeDiShi()
            self.nayin_list = [self.year_nayin, self.month_nayin, self.day_nayin, self.hour_nayin]
            self.dishi_list = [self.year_dishi, self.month_dishi, self.day_dishi, self.hour_dishi]
            self.hour_zizuo_dishi = self.check_dishi(self.hour_zhu)
            self.dishi_zizuo_list = [self.year_zizuo_dishi, self.month_zizuo_dishi, self.day_zizuo_dishi, self.hour_zizuo_dishi]
            self.xunkong_list = [self._lunar.getYearXunKongExact(), self._lunar.getMonthXunKongExact(), self._lunar.getDayXunKongExact(), self._lunar.getTimeXunKong()]
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
            self.xunkong_list = [self._lunar.getYearXunKongExact(), self._lunar.getMonthXunKongExact(), self._lunar.getDayXunKongExact()]
        self.is_special = False
        self.refer = None
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
        gan = zhu.gan._gan
        zhi = zhu.zhi._zhi
        CHANG_SHENG = ("长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养")

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
    
    def switch_shensha(self, shishen):
        switch_shensha = {"七杀": "杀", "正官": "官", "正印": "印", "偏印": "枭", "比肩": "比", "劫财": "劫", "正财": "财", "偏财": "才", "食神": "食", "伤官": "伤"}
        return switch_shensha[shishen.chinese_name]

    def generate_ganzhi_and_shishen_for_yun_nian(self, target, ganzhi, gan_list_rear = None, zhi_list_rear = None):
        target["gan"] = ganzhi[0]
        target["zhi"] = ganzhi[1]
        target["gan_wuxing"] = Gan.from_chinese(ganzhi[0]).wuxing.chinese_name
        target["zhi_wuxing"] = Zhi.from_chinese(ganzhi[1]).wuxing.chinese_name
        target["gan_shishen"] = self.switch_shensha(self.calculate_shishen(self.day_gan._gan, Gan.from_chinese(ganzhi[0])))
        target["zhi_shishen"] = self.switch_shensha(self.calculate_shishen(self.day_gan._gan, Zhi.from_chinese(ganzhi[1]).hidden_gans[0]))
        if gan_list_rear:
            target["gan_relation"] = Gan.from_chinese(ganzhi[0]).get_wuhe_relations(gan_list_rear)
            target["zhi_relation"] = Zhi.from_chinese(ganzhi[1]).get_relations(zhi_list_rear)

    def calculate_dayun_liunian(self):
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
                ganzhi = liunian.getGanZhi()
                self.generate_ganzhi_and_shishen_for_yun_nian(liunian_res, ganzhi, gan_list_rear, zhi_list_rear)
                liunian_res["age"] = liunian.getAge()
                liunian_res["year"] = liunian.getYear()
                liunian_word = f"{liunian.getYear()}{ganzhi}【{liunian_res['gan_shishen']}{liunian_res['zhi_shishen']}】{liunian.getAge()}岁："

                liunian_res["liuyue"] = []
                liunina_lunar = Lunar.fromYmd(liunian_res["year"],6,1)
                jieqi = liunina_lunar.getJieQiTable()
                jie_name_list = ["立春", "惊蛰", "清明", "立夏", "芒种", "小暑", "立秋", "白露", "寒露", "立冬", "大雪", "XIAO_HAN"]
                liuyue_list = liunian.getLiuYue()
                gan_list_rear.append(Gan.from_chinese(ganzhi[0]))
                zhi_list_rear.append(Zhi.from_chinese(ganzhi[1]))
                for i in range(12):
                    liuyue_res = dict()
                    jie_time = jieqi[jie_name_list[i]]
                    liuyue_res["month"] = jie_time.getMonth()
                    liuyue_res["day"] = jie_time.getDay()
                    ganzhi = liuyue_list[i].getGanZhi()
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
