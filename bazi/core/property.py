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

# bazi_core\property.py

from enum import Enum

class Yinyang(Enum):
    YIN = 0
    YANG = 1

    @property
    def chinese_name(self):
        return "阴" if self == Yinyang.YIN else "阳"
    
class Wuxing(Enum):
    MU = 0
    HUO = 1
    TU = 2
    JIN = 3
    SHUI = 4

    @property
    def chinese_name(self):
        chinese_names = ["木", "火", "土", "金", "水"]
        return chinese_names[self.value]

class Gan(Enum):
    JIA = 0
    YI = 1
    BING = 2
    DING = 3
    WU = 4
    JI = 5
    GENG = 6
    XIN = 7
    REN = 8
    GUI = 9

    @property
    def yinyang(self):
        return Yinyang.YANG if self.value % 2 == 0 else Yinyang.YIN

    @property
    def wuxing(self):
        return Wuxing(self.value // 2)

    @property
    def chinese_name(self):
        chinese_names = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        return chinese_names[self.value]

    @classmethod
    def from_chinese(cls, name):
        chinese_names = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        return cls(chinese_names.index(name))
    
    def get_wuhe_relations(self, other_gans):
        """获取与当前天干形成五合的关系（简化版）"""
        wuhe_pairs = [
            (Gan.JIA, Gan.JI),    # 甲己合
            (Gan.YI, Gan.GENG),   # 乙庚合
            (Gan.BING, Gan.XIN),  # 丙辛合
            (Gan.DING, Gan.REN),  # 丁壬合
            (Gan.WU, Gan.GUI)    # 戊癸合
        ]
        
        relations = []
        for gan1, gan2 in wuhe_pairs:
            if self == gan1 and gan2 in other_gans:
                relations.append(f"{gan1.chinese_name}{gan2.chinese_name}五合")
            elif self == gan2 and gan1 in other_gans:
                relations.append(f"{gan1.chinese_name}{gan2.chinese_name}五合")
        
        # 去重处理
        return list(dict.fromkeys(relations))

class Zhi(Enum):
    ZI = 0
    CHOU = 1
    YIN = 2
    MAO = 3
    CHEN = 4
    SI = 5
    WU = 6
    WEI = 7
    SHEN = 8
    YOU = 9
    XU = 10
    HAI = 11

    @property
    def yinyang(self):
        return Yinyang.YANG if self.value % 2 == 0 else Yinyang.YIN

    @property
    def wuxing(self):
        return Wuxing(2 if (self.value + 2) % 3 == 0 else ((self.value + 4) % 12 // 3 + 3) % 5)

    @property
    def chinese_name(self):
        chinese_names = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        return chinese_names[self.value]

    @property
    def hidden_gans(self):
        zhi_hidden_gan = {
            0: ["癸"],
            1: ["己", "癸", "辛"],
            2: ["甲", "丙", "戊"],
            3: ["乙"],
            4: ["戊", "乙", "癸"],
            5: ["丙", "庚", "戊"],
            6: ["丁", "己"],
            7: ["己", "丁", "乙"],
            8: ["庚", "壬", "戊"],
            9: ["辛"],
            10: ["戊", "辛", "丁"],
            11: ["壬", "甲"]
        }
        return [Gan.from_chinese(g) for g in zhi_hidden_gan[self.value]]

    def get_hidden_gans_shishen(self, day_gan):
        return [get_shishen_type(day_gan.chinese_name, gan.chinese_name) for gan in self.hidden_gans]

    @classmethod
    def from_chinese(cls, name):
        chinese_names = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        return cls(chinese_names.index(name))

    def get_relations(self, other_zhis):
        relations = []
        current = self
        all_zhis = other_zhis + [current]
        
        # 三会检查（保持原有逻辑，自动排序）
        sanhui_groups = [
            (Zhi.YIN, Zhi.MAO, Zhi.CHEN),  # 寅卯辰会木
            (Zhi.SI, Zhi.WU, Zhi.WEI),     # 巳午未会火
            (Zhi.SHEN, Zhi.YOU, Zhi.XU),   # 申酉戌会金
            (Zhi.HAI, Zhi.ZI, Zhi.CHOU)    # 亥子丑会水
        ]
        for group in sanhui_groups:
            if current in group and all(z in all_zhis for z in group):
                ordered = sorted(group, key=lambda z: z.value)
                relations.append(f"{''.join(z.chinese_name for z in ordered)}三会")

        # 三合与拱合（新增排序逻辑）
        sanhe_groups = [
            (Zhi.HAI, Zhi.MAO, Zhi.WEI),
            (Zhi.YIN, Zhi.WU, Zhi.XU),
            (Zhi.SI, Zhi.YOU, Zhi.CHOU),
            (Zhi.SHEN, Zhi.ZI, Zhi.CHEN)
        ]
        for group in sanhe_groups:
            if current in group:
                # 完整三合
                if all(z in all_zhis for z in group):
                    ordered = sorted(group, key=lambda z: z.value)
                    relations.append(f"{''.join(z.chinese_name for z in ordered)}三合")
                else:
                    # 处理拱合（首尾存在）
                    if current == group[0] and group[2] in all_zhis:
                        pair = sorted([current, group[2]], key=lambda z: z.value)
                        relations.append(f"{pair[0].chinese_name}{pair[1].chinese_name}拱合")
                    # 处理半合（确保顺序）
                    if current == group[0] and group[1] in all_zhis:
                        relations.append(f"{current.chinese_name}{group[1].chinese_name}半合")
                    elif current == group[2] and group[1] in all_zhis:
                        relations.append(f"{group[1].chinese_name}{current.chinese_name}半合")

        # 三刑与相刑（关键改动点）
        sanxing_groups = [
            (Zhi.YIN, Zhi.SI, Zhi.SHEN),  # 寅巳申三刑
            (Zhi.CHOU, Zhi.WEI, Zhi.XU),  # 丑未戌三刑
            (Zhi.ZI, Zhi.MAO)             # 子卯刑
        ]
        for group in sanxing_groups:
            if current in group:
                existing = [z for z in group if z in all_zhis and z != current]
                if len(existing) >= 1:
                    # 生成有序组合
                    sorted_group = sorted([current] + existing, key=lambda z: z.value)
                    # 三刑优先
                    if len(sorted_group) >=3 and len(group)==3:
                        relations.append(f"{''.join(z.chinese_name for z in sorted_group[:3])}三刑")
                    else:
                        # 两两相刑
                        for z in sorted_group[1:]:
                            if z != current:
                                pair = sorted([current, z], key=lambda z: z.value)
                                relations.append(f"{pair[0].chinese_name}{pair[1].chinese_name}刑")

        # 自刑（无需修改）
        if current in [Zhi.CHEN, Zhi.WU, Zhi.YOU, Zhi.HAI] and all_zhis.count(current)>=2:
            relations.append(f"{current.chinese_name}{current.chinese_name}自刑")

        # 六合（调整顺序生成）
        liuhe_pairs = {
            (Zhi.ZI, Zhi.CHOU),
            (Zhi.YIN, Zhi.HAI),
            (Zhi.MAO, Zhi.XU),
            (Zhi.CHEN, Zhi.YOU),
            (Zhi.SI, Zhi.SHEN),
            (Zhi.WU, Zhi.WEI)
        }
        for pair in liuhe_pairs:
            if current in pair and any(z in all_zhis for z in pair if z != current):
                ordered = sorted(pair, key=lambda z: z.value)
                relations.append(f"{ordered[0].chinese_name}{ordered[1].chinese_name}六合")

        # 六冲（调整顺序生成）
        liuchong_pairs = {
            (Zhi.ZI, Zhi.WU),
            (Zhi.CHOU, Zhi.WEI),
            (Zhi.YIN, Zhi.SHEN),
            (Zhi.MAO, Zhi.YOU),
            (Zhi.CHEN, Zhi.XU),
            (Zhi.SI, Zhi.HAI)
        }
        for pair in liuchong_pairs:
            if current in pair and any(z in all_zhis for z in pair if z != current):
                ordered = sorted(pair, key=lambda z: z.value)
                relations.append(f"{ordered[0].chinese_name}{ordered[1].chinese_name}冲")

        # 六害（调整顺序生成）
        liuhai_pairs = {
            (Zhi.ZI, Zhi.WEI),
            (Zhi.CHOU, Zhi.WU),
            (Zhi.YIN, Zhi.SI),
            (Zhi.MAO, Zhi.CHEN),
            (Zhi.SHEN, Zhi.HAI),
            (Zhi.YOU, Zhi.XU)
        }
        for pair in liuhai_pairs:
            if current in pair and any(z in all_zhis for z in pair if z != current):
                ordered = sorted(pair, key=lambda z: z.value)
                relations.append(f"{ordered[0].chinese_name}{ordered[1].chinese_name}害")

        # 相破（调整顺序生成）
        xiangpo_pairs = {
            (Zhi.ZI, Zhi.YOU),
            (Zhi.YIN, Zhi.HAI),
            (Zhi.CHEN, Zhi.CHOU),
            (Zhi.WU, Zhi.MAO),
            (Zhi.SHEN, Zhi.SI),
            (Zhi.XU, Zhi.WEI)
        }
        for pair in xiangpo_pairs:
            if current in pair and any(z in all_zhis for z in pair if z != current):
                ordered = sorted(pair, key=lambda z: z.value)
                relations.append(f"{ordered[0].chinese_name}{ordered[1].chinese_name}破")

        # 最终去重（仅简单去重，无需排序处理）
        seen = set()
        return [rel for rel in relations if not (rel in seen or seen.add(rel))]

class Shishen(Enum):
    RIZHU = -1
    BIJIAN = 0
    JIECAI = 1
    SHISHEN = 2
    SHANGGUAN = 3
    PIANCAI = 4
    ZHENGCAI = 5
    QISHA = 6
    ZHENGGUAN = 7
    PIANYIN = 8
    ZHENGYIN = 9

    @property
    def chinese_name(self):
        chinese_names = ["日主", "比肩", "劫财", "食神", "伤官", "偏财", "正财", "七杀", "正官", "偏印", "正印"]
        return chinese_names[self.value + 1]  # Adjusting the index for RIZHU

class Zhu:
    def __init__(self, gan, zhi):
        self.gan = gan
        self.zhi = zhi

    @property
    def chinese_name(self):
        return f"{self.gan.get().chinese_name}{self.zhi.get().chinese_name}"

    def __repr__(self):
        return f"Zhu(gan={self.gan.get().name}, zhi={self.zhi.get().name})"

class Area(Enum):
    LOVE = "婚恋"
    CAREER = "事业"
    STUDY = "学业"
    HEALTH = "健康"
    WEALTH = "财富"
    FAMILY = "家庭"
    SOCIAL = "社交"
    CHARACTER = "性格"
    TALENT = "天赋"
    REPUTATION = "名誉"
    FORTUNE = "福气"
    CHILDREN = "子女"
    YUN = "运"
    OTHER = "其他"


class Condition(Enum):
    YEAR_GAN = "年干"
    YEAR_ZHI = "年支"
    MONTH_GAN = "月干"
    MONTH_ZHI = "月支"
    DAY_GAN = "日干"
    DAY_ZHI = "日支"
    HOUR_GAN = "时干"
    HOUR_ZHI = "时支"
    YEAR_ZHU = "年柱"
    MONTH_ZHU = "月柱"
    DAY_ZHU = "日柱"
    HOUR_ZHU = "时柱"
    EXCESS = "过多"
    SITTING_ON_EMPTY = "坐空亡"
    SITTING_ON_YANGREN = "坐羊刃"
    SITTING_ON_SANXING = "坐三刑"
    SITTING_ON_CHONG = "坐冲"
    SITTING_ON_JUE = "坐绝"
    LACK = "缺少"
    OTHER = "其他"

def get_gan_wuxing_yinyang(wuxing, yinyang):
    for gan in Gan:
        if gan.wuxing == wuxing and gan.yinyang == yinyang:
            return gan

def get_tiangandizhi_state(gan, state_type):
    # 定义每个天干在十二种状态下对应的地支
    positions = {
        Gan.JIA: ["亥", "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌"],
        Gan.YI: ["午", "巳", "辰", "卯", "寅", "丑", "子", "亥", "戌", "酉", "申", "未"],
        Gan.BING: ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"],
        Gan.DING: ["酉", "申", "未", "午", "巳", "辰", "卯", "寅", "丑", "子", "亥", "戌"],
        Gan.WU: ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"],
        Gan.JI: ["酉", "申", "未", "午", "巳", "辰", "卯", "寅", "丑", "子", "亥", "戌"],
        Gan.GENG: ["巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑", "寅", "卯", "辰"],
        Gan.XIN: ["子", "亥", "戌", "酉", "申", "未", "午", "巳", "辰", "卯", "寅", "丑"],
        Gan.REN: ["申", "酉", "戌", "亥", "子", "丑", "寅", "卯", "辰", "巳", "午", "未"],
        Gan.GUI: ["卯", "寅", "丑", "子", "亥", "戌", "酉", "申", "未", "午", "巳", "辰"]
    }

    # 状态类型与索引的映射
    state_index = {
        "长生": 0,
        "沐浴": 1,
        "冠带": 2,
        "临官": 3,
        "帝旺": 4,
        "衰": 5,
        "病": 6,
        "死": 7,
        "墓": 8,
        "绝": 9,
        "胎": 10,
        "养": 11
    }

    # 获取对应的地支状态
    gan_positions = positions.get(gan)
    if not gan_positions:
        return None

    # 获取状态索引
    index = state_index.get(state_type)
    if index is None:
        return None

    # 返回指定的状态类型的地支
    zhi_name = gan_positions[index]
    return Zhi.from_chinese(zhi_name)

def get_shishen_gan(gan, shishen):
    # 定义天干
    tiangan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

    # 定义十神对应表
    shishen_table = {
        "甲": ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"],
        "乙": ["乙", "甲", "丁", "丙", "己", "戊", "辛", "庚", "癸", "壬"],
        "丙": ["丙", "丁", "戊", "己", "庚", "辛", "壬", "癸", "甲", "乙"],
        "丁": ["丁", "丙", "己", "戊", "辛", "庚", "癸", "壬", "乙", "甲"],
        "戊": ["戊", "己", "庚", "辛", "壬", "癸", "甲", "乙", "丙", "丁"],
        "己": ["己", "戊", "辛", "庚", "癸", "壬", "乙", "甲", "丁", "丙"],
        "庚": ["庚", "辛", "壬", "癸", "甲", "乙", "丙", "丁", "戊", "己"],
        "辛": ["辛", "庚", "癸", "壬", "乙", "甲", "丁", "丙", "己", "戊"],
        "壬": ["壬", "癸", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛"],
        "癸": ["癸", "壬", "乙", "甲", "丁", "丙", "己", "戊", "辛", "庚"]
    }

    # 定义十神顺序
    shishen_list = ["比肩", "劫财", "食神", "伤官", "偏财", "正财", "七杀", "正官", "偏印", "正印"]

    if gan not in tiangan or shishen not in shishen_list:
        return None

    gan_index = tiangan.index(gan)
    shishen_index = shishen_list.index(shishen)
    
    return shishen_table[gan][shishen_index]

def get_shishen_type(gan1, gan2):
    # 定义天干
    tiangan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

    # 定义十神对应表
    shishen_table = {
        "甲": ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"],
        "乙": ["乙", "甲", "丁", "丙", "己", "戊", "辛", "庚", "癸", "壬"],
        "丙": ["丙", "丁", "戊", "己", "庚", "辛", "壬", "癸", "甲", "乙"],
        "丁": ["丁", "丙", "己", "戊", "辛", "庚", "癸", "壬", "乙", "甲"],
        "戊": ["戊", "己", "庚", "辛", "壬", "癸", "甲", "乙", "丙", "丁"],
        "己": ["己", "戊", "辛", "庚", "癸", "壬", "乙", "甲", "丁", "丙"],
        "庚": ["庚", "辛", "壬", "癸", "甲", "乙", "丙", "丁", "戊", "己"],
        "辛": ["辛", "庚", "癸", "壬", "乙", "甲", "丁", "丙", "己", "戊"],
        "壬": ["壬", "癸", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛"],
        "癸": ["癸", "壬", "乙", "甲", "丁", "丙", "己", "戊", "辛", "庚"]
    }

    # 定义十神顺序
    shishen_list = ["比肩", "劫财", "食神", "伤官", "偏财", "正财", "七杀", "正官", "偏印", "正印"]

    if gan1 not in tiangan or gan2 not in tiangan:
        return None

    shishen_gans = shishen_table[gan1]
    if gan2 in shishen_gans:
        shishen_index = shishen_gans.index(gan2)
        return shishen_list[shishen_index]
    return None

def get_shengxiao_by_zhi_name(zhi_name):
    shengxiao_table = {
        "子": "鼠",
        "丑": "牛",
        "寅": "虎",
        "卯": "兔",
        "辰": "龙",
        "巳": "蛇",
        "午": "马",
        "未": "羊",
        "申": "猴",
        "酉": "鸡",
        "戌": "狗",
        "亥": "猪",
    }
    return shengxiao_table[zhi_name]
