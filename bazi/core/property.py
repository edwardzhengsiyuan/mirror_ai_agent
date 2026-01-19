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

# ----------------------------
# API enum serialization helpers
# ----------------------------
# 为了支持下游服务做多语言映射，所有“可枚举语义字段”可统一输出为带命名空间的枚举码：
#   "GAN:WU", "ZHI:WU", "SHENSHA:TIANYI", ...
# 下游只需按 namespace + code 查语言包即可，且能避免 Gan/Zhi 等同名冲突。

NS_YINYANG = "YINYANG"
NS_WUXING = "WUXING"
NS_GAN = "GAN"
NS_ZHI = "ZHI"
NS_SHISHEN = "SHISHEN"
NS_SHENGXIAO = "SHENGXIAO"
NS_SHENSHA = "SHENSHA"
NS_NAYIN = "NAYIN"
NS_DISHI = "DISHI"
NS_SHENQIANGRUO = "SHENQIANGRUO"
NS_GEJU = "GEJU"
NS_GAN_RELATION_TYPE = "GAN_RELATION_TYPE"
NS_ZHI_RELATION_TYPE = "ZHI_RELATION_TYPE"
NS_ZODIAC_COMPAT_RELATION = "ZODIAC_COMPAT_RELATION"
NS_ZODIAC_COMPAT_FAVORABILITY = "ZODIAC_COMPAT_FAVORABILITY"
NS_ZODIAC_COMPAT_DETAIL = "ZODIAC_COMPAT_DETAIL"


def ns(namespace: str, code: str | None) -> str | None:
    """
    将枚举码包装为带命名空间的字符串：f"{namespace}:{code}"。
    为了幂等，如果 code 已经包含 ":"（认为已命名空间化），则原样返回。
    """
    if code is None:
        return None
    if not isinstance(code, str):
        return code  # type: ignore[return-value]
    if ":" in code:
        return code
    return f"{namespace}:{code}"


def strip_ns(value: str | None) -> str | None:
    """把 'GAN:WU' 还原为 'WU'；若不含 ':' 则原样返回。"""
    if value is None:
        return None
    if not isinstance(value, str):
        return value  # type: ignore[return-value]
    if ":" not in value:
        return value
    return value.split(":", 1)[1]

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

    @classmethod
    def from_chinese_name(cls, name: str) -> "Wuxing":
        mapping = {
            "木": cls.MU,
            "火": cls.HUO,
            "土": cls.TU,
            "金": cls.JIN,
            "水": cls.SHUI,
        }
        return mapping[name.strip()]

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

    def get_wuhe_relations_enum(self, other_gans: list["Gan"]) -> list[dict]:
        """
        返回天干五合关系（结构化枚举）。

        形如：
        [
          {"type": "WUHE", "members": ["JIA","JI"]}
        ]
        """
        wuhe_pairs = [
            (Gan.JIA, Gan.JI),
            (Gan.YI, Gan.GENG),
            (Gan.BING, Gan.XIN),
            (Gan.DING, Gan.REN),
            (Gan.WU, Gan.GUI),
        ]
        seen = set()
        res: list[dict] = []
        for g1, g2 in wuhe_pairs:
            if (self == g1 and g2 in other_gans) or (self == g2 and g1 in other_gans):
                ordered = sorted([g1, g2], key=lambda x: x.value)
                key = (GanRelationType.WUHE.name, ordered[0].name, ordered[1].name)
                if key in seen:
                    continue
                seen.add(key)
                res.append({"type": GanRelationType.WUHE.name, "members": [ordered[0].name, ordered[1].name]})
        return res

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
    def shengxiao(self) -> "Shengxiao":
        mapping = {
            Zhi.ZI: Shengxiao.SHU,
            Zhi.CHOU: Shengxiao.NIU,
            Zhi.YIN: Shengxiao.HU,
            Zhi.MAO: Shengxiao.TU,
            Zhi.CHEN: Shengxiao.LONG,
            Zhi.SI: Shengxiao.SHE,
            Zhi.WU: Shengxiao.MA,
            Zhi.WEI: Shengxiao.YANG,
            Zhi.SHEN: Shengxiao.HOU,
            Zhi.YOU: Shengxiao.JI,
            Zhi.XU: Shengxiao.GOU,
            Zhi.HAI: Shengxiao.ZHU,
        }
        return mapping[self]

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

    def get_relations_enum(self, other_zhis: list["Zhi"]) -> list[dict]:
        """
        返回地支关系（结构化枚举），所有输出字段均为枚举值（字符串）。

        形如：
        [
          {"type": "LIUHE", "members": ["ZI","CHOU"]},
          {"type": "SANHE", "members": ["SHEN","ZI","CHEN"]}
        ]
        """
        current = self
        all_zhis = other_zhis + [current]
        res: list[dict] = []
        seen = set()

        def _add(rel_type: "ZhiRelationType", members: list["Zhi"]):
            ordered = sorted(members, key=lambda z: z.value)
            key = (rel_type.name, tuple(z.name for z in ordered))
            if key in seen:
                return
            seen.add(key)
            res.append({"type": rel_type.name, "members": [z.name for z in ordered]})

        # 三会
        sanhui_groups = [
            (Zhi.YIN, Zhi.MAO, Zhi.CHEN),
            (Zhi.SI, Zhi.WU, Zhi.WEI),
            (Zhi.SHEN, Zhi.YOU, Zhi.XU),
            (Zhi.HAI, Zhi.ZI, Zhi.CHOU),
        ]
        for group in sanhui_groups:
            if current in group and all(z in all_zhis for z in group):
                _add(ZhiRelationType.SANHUI, list(group))

        # 三合 / 半合 / 拱合
        sanhe_groups = [
            (Zhi.HAI, Zhi.MAO, Zhi.WEI),
            (Zhi.YIN, Zhi.WU, Zhi.XU),
            (Zhi.SI, Zhi.YOU, Zhi.CHOU),
            (Zhi.SHEN, Zhi.ZI, Zhi.CHEN),
        ]
        for group in sanhe_groups:
            if current not in group:
                continue
            if all(z in all_zhis for z in group):
                _add(ZhiRelationType.SANHE, list(group))
            else:
                # 拱合：首尾存在
                if current == group[0] and group[2] in all_zhis:
                    _add(ZhiRelationType.GONGHE, [group[0], group[2]])
                # 半合：与中神同现
                if current == group[0] and group[1] in all_zhis:
                    _add(ZhiRelationType.BANHE, [group[0], group[1]])
                elif current == group[2] and group[1] in all_zhis:
                    _add(ZhiRelationType.BANHE, [group[1], group[2]])

        # 三刑 / 刑
        sanxing_groups = [
            (Zhi.YIN, Zhi.SI, Zhi.SHEN),
            (Zhi.CHOU, Zhi.WEI, Zhi.XU),
            (Zhi.ZI, Zhi.MAO),
        ]
        for group in sanxing_groups:
            if current not in group:
                continue
            existing = [z for z in group if z in all_zhis and z != current]
            if not existing:
                continue
            if len(group) == 3 and len(existing) >= 2:
                _add(ZhiRelationType.SANXING, [current] + existing[:2])
            else:
                for z in existing:
                    _add(ZhiRelationType.XING, [current, z])

        # 自刑
        if current in [Zhi.CHEN, Zhi.WU, Zhi.YOU, Zhi.HAI] and all_zhis.count(current) >= 2:
            _add(ZhiRelationType.ZIXING, [current, current])

        # 六合
        liuhe_pairs = [
            (Zhi.ZI, Zhi.CHOU),
            (Zhi.YIN, Zhi.HAI),
            (Zhi.MAO, Zhi.XU),
            (Zhi.CHEN, Zhi.YOU),
            (Zhi.SI, Zhi.SHEN),
            (Zhi.WU, Zhi.WEI),
        ]
        for a, b in liuhe_pairs:
            if current in (a, b) and any(z in all_zhis for z in (a, b) if z != current):
                _add(ZhiRelationType.LIUHE, [a, b])

        # 六冲
        liuchong_pairs = [
            (Zhi.ZI, Zhi.WU),
            (Zhi.CHOU, Zhi.WEI),
            (Zhi.YIN, Zhi.SHEN),
            (Zhi.MAO, Zhi.YOU),
            (Zhi.CHEN, Zhi.XU),
            (Zhi.SI, Zhi.HAI),
        ]
        for a, b in liuchong_pairs:
            if current in (a, b) and any(z in all_zhis for z in (a, b) if z != current):
                _add(ZhiRelationType.LIUCHONG, [a, b])

        # 六害
        liuhai_pairs = [
            (Zhi.ZI, Zhi.WEI),
            (Zhi.CHOU, Zhi.WU),
            (Zhi.YIN, Zhi.SI),
            (Zhi.MAO, Zhi.CHEN),
            (Zhi.SHEN, Zhi.HAI),
            (Zhi.YOU, Zhi.XU),
        ]
        for a, b in liuhai_pairs:
            if current in (a, b) and any(z in all_zhis for z in (a, b) if z != current):
                _add(ZhiRelationType.LIUHAI, [a, b])

        # 相破
        xiangpo_pairs = [
            (Zhi.ZI, Zhi.YOU),
            (Zhi.YIN, Zhi.HAI),
            (Zhi.CHEN, Zhi.CHOU),
            (Zhi.WU, Zhi.MAO),
            (Zhi.SHEN, Zhi.SI),
            (Zhi.XU, Zhi.WEI),
        ]
        for a, b in xiangpo_pairs:
            if current in (a, b) and any(z in all_zhis for z in (a, b) if z != current):
                _add(ZhiRelationType.XIANGPO, [a, b])

        return res


class ShenQiangRuo(Enum):
    QIANG = "QIANG"
    ZHONGHE = "ZHONGHE"
    RUO = "RUO"

    @property
    def chinese_name(self) -> str:
        mapping = {
            ShenQiangRuo.QIANG: "日主强",
            ShenQiangRuo.ZHONGHE: "日主中和",
            ShenQiangRuo.RUO: "日主弱",
        }
        return mapping[self]


class GanRelationType(Enum):
    WUHE = "WUHE"


class ZhiRelationType(Enum):
    SANHUI = "SANHUI"
    SANHE = "SANHE"
    BANHE = "BANHE"
    GONGHE = "GONGHE"
    SANXING = "SANXING"
    XING = "XING"
    ZIXING = "ZIXING"
    LIUHE = "LIUHE"
    LIUCHONG = "LIUCHONG"
    LIUHAI = "LIUHAI"
    XIANGPO = "XIANGPO"


class GejuEnum(Enum):
    NEED_MORE_ANALYSIS = "NEED_MORE_ANALYSIS"
    ZHUANWANG_GE = "ZHUANWANG_GE"
    YANGREN_GE = "YANGREN_GE"
    LUSHEN_GE = "LUSHEN_GE"

    BIJIAN_GE = "BIJIAN_GE"
    JIECAI_GE = "JIECAI_GE"
    SHISHEN_GE = "SHISHEN_GE"
    SHANGGUAN_GE = "SHANGGUAN_GE"
    PIANCAI_GE = "PIANCAI_GE"
    ZHENGCAI_GE = "ZHENGCAI_GE"
    QISHA_GE = "QISHA_GE"
    ZHENGGUAN_GE = "ZHENGGUAN_GE"
    PIANYIN_GE = "PIANYIN_GE"
    ZHENGYIN_GE = "ZHENGYIN_GE"

    @property
    def chinese_name(self) -> str:
        mapping = {
            GejuEnum.NEED_MORE_ANALYSIS: "需要进一步分析",
            GejuEnum.ZHUANWANG_GE: "专旺格",
            GejuEnum.YANGREN_GE: "羊刃格",
            GejuEnum.LUSHEN_GE: "禄神格",
            GejuEnum.BIJIAN_GE: "比肩格",
            GejuEnum.JIECAI_GE: "劫财格",
            GejuEnum.SHISHEN_GE: "食神格",
            GejuEnum.SHANGGUAN_GE: "伤官格",
            GejuEnum.PIANCAI_GE: "偏财格",
            GejuEnum.ZHENGCAI_GE: "正财格",
            GejuEnum.QISHA_GE: "七杀格",
            GejuEnum.ZHENGGUAN_GE: "正官格",
            GejuEnum.PIANYIN_GE: "偏印格",
            GejuEnum.ZHENGYIN_GE: "正印格",
        }
        return mapping[self]

    @classmethod
    def from_shishen(cls, shishen: "Shishen") -> "GejuEnum":
        mapping = {
            Shishen.BIJIAN: cls.BIJIAN_GE,
            Shishen.JIECAI: cls.JIECAI_GE,
            Shishen.SHISHEN: cls.SHISHEN_GE,
            Shishen.SHANGGUAN: cls.SHANGGUAN_GE,
            Shishen.PIANCAI: cls.PIANCAI_GE,
            Shishen.ZHENGCAI: cls.ZHENGCAI_GE,
            Shishen.QISHA: cls.QISHA_GE,
            Shishen.ZHENGGUAN: cls.ZHENGGUAN_GE,
            Shishen.PIANYIN: cls.PIANYIN_GE,
            Shishen.ZHENGYIN: cls.ZHENGYIN_GE,
        }
        return mapping[shishen]


class Shengxiao(Enum):
    SHU = "SHU"
    NIU = "NIU"
    HU = "HU"
    TU = "TU"
    LONG = "LONG"
    SHE = "SHE"
    MA = "MA"
    YANG = "YANG"
    HOU = "HOU"
    JI = "JI"
    GOU = "GOU"
    ZHU = "ZHU"


class ZodiacCompatibilityRelation(Enum):
    SAME = "SAME"
    LIUHE = "LIUHE"
    SANHE = "SANHE"
    LIUCHONG = "LIUCHONG"
    LIUHAI = "LIUHAI"
    NEUTRAL = "NEUTRAL"


class ZodiacCompatibilityFavorability(Enum):
    FAVORABLE = "FAVORABLE"
    UNFAVORABLE = "UNFAVORABLE"
    NEUTRAL = "NEUTRAL"


class ZodiacCompatibilityDetail(Enum):
    SAME = "SAME"
    LIUHE = "LIUHE"
    SANHE = "SANHE"
    LIUCHONG = "LIUCHONG"
    LIUHAI = "LIUHAI"
    NEUTRAL = "NEUTRAL"


class ShenshaEnum(Enum):
    GUCHEN = "GUCHEN"
    GUASU = "GUASU"
    HONGLUAN = "HONGLUAN"
    TIANXI = "TIANXI"
    TIANDEGUIREN = "TIANDEGUIREN"
    YUEDE = "YUEDE"
    TIANYI = "TIANYI"
    WENCHANG = "WENCHANG"
    YANGREN = "YANGREN"
    LUSHEN = "LUSHEN"
    HONGYAN = "HONGYAN"
    JIANGXING = "JIANGXING"
    HUAGAI = "HUAGAI"
    YIMA = "YIMA"
    JIESHA = "JIESHA"
    WANGSHEN = "WANGSHEN"
    TAOHUA = "TAOHUA"
    TAIJIGUIREN = "TAIJIGUIREN"
    KONGWANG = "KONGWANG"
    SANQIGUIREN = "SANQIGUIREN"
    FUXINGGUIREN = "FUXINGGUIREN"
    KUIGANG = "KUIGANG"
    GUOYINGUIREN = "GUOYINGUIREN"
    DEXIUGUIREN = "DEXIUGUIREN"
    XUETANG = "XUETANG"
    CIGUAN = "CIGUAN"
    TIANCHUGUIREN = "TIANCHUGUIREN"
    JINYU = "JINYU"
    ZAISHA = "ZAISHA"
    BAZHUAN = "BAZHUAN"
    TONGZI = "TONGZI"
    YINCHAYANCUO = "YINCHAYANCUO"
    SHIEDABAI = "SHIEDABAI"
    TIANYII = "TIANYII"


class Nayin(Enum):
    HAI_ZHONG_JIN = "HAI_ZHONG_JIN"
    LU_ZHONG_HUO = "LU_ZHONG_HUO"
    DA_LIN_MU = "DA_LIN_MU"
    LU_PANG_TU = "LU_PANG_TU"
    JIAN_FENG_JIN = "JIAN_FENG_JIN"
    SHAN_TOU_HUO = "SHAN_TOU_HUO"
    JIAN_XIA_SHUI = "JIAN_XIA_SHUI"
    CHENG_TOU_TU = "CHENG_TOU_TU"
    BAI_LA_JIN = "BAI_LA_JIN"
    YANG_LIU_MU = "YANG_LIU_MU"
    QUAN_ZHONG_SHUI = "QUAN_ZHONG_SHUI"
    WU_SHANG_TU = "WU_SHANG_TU"
    PI_LI_HUO = "PI_LI_HUO"
    SONG_BAI_MU = "SONG_BAI_MU"
    CHANG_LIU_SHUI = "CHANG_LIU_SHUI"
    SHA_ZHONG_JIN = "SHA_ZHONG_JIN"
    SHAN_XIA_HUO = "SHAN_XIA_HUO"
    PING_DI_MU = "PING_DI_MU"
    BI_SHANG_TU = "BI_SHANG_TU"
    JIN_BO_JIN = "JIN_BO_JIN"
    FO_DENG_HUO = "FO_DENG_HUO"
    TIAN_HE_SHUI = "TIAN_HE_SHUI"
    DA_YI_TU = "DA_YI_TU"
    CHAI_CHUAN_JIN = "CHAI_CHUAN_JIN"
    SANG_ZHE_MU = "SANG_ZHE_MU"
    DA_XI_SHUI = "DA_XI_SHUI"
    SHA_ZHONG_TU = "SHA_ZHONG_TU"
    TIAN_SHANG_HUO = "TIAN_SHANG_HUO"
    SHI_LIU_MU = "SHI_LIU_MU"
    DA_HAI_SHUI = "DA_HAI_SHUI"

    @classmethod
    def from_chinese_name(cls, name: str) -> "Nayin":
        mapping = {
            "海中金": cls.HAI_ZHONG_JIN,
            "炉中火": cls.LU_ZHONG_HUO,
            "大林木": cls.DA_LIN_MU,
            "路旁土": cls.LU_PANG_TU,
            "剑锋金": cls.JIAN_FENG_JIN,
            "山头火": cls.SHAN_TOU_HUO,
            "涧下水": cls.JIAN_XIA_SHUI,
            "城头土": cls.CHENG_TOU_TU,
            "白蜡金": cls.BAI_LA_JIN,
            "杨柳木": cls.YANG_LIU_MU,
            "泉中水": cls.QUAN_ZHONG_SHUI,
            "屋上土": cls.WU_SHANG_TU,
            "霹雳火": cls.PI_LI_HUO,
            "松柏木": cls.SONG_BAI_MU,
            "长流水": cls.CHANG_LIU_SHUI,
            "砂中金": cls.SHA_ZHONG_JIN,
            "山下火": cls.SHAN_XIA_HUO,
            "平地木": cls.PING_DI_MU,
            "壁上土": cls.BI_SHANG_TU,
            "金箔金": cls.JIN_BO_JIN,
            "佛灯火": cls.FO_DENG_HUO,
            "天河水": cls.TIAN_HE_SHUI,
            "大驿土": cls.DA_YI_TU,
            "钗钏金": cls.CHAI_CHUAN_JIN,
            "桑柘木": cls.SANG_ZHE_MU,
            "大溪水": cls.DA_XI_SHUI,
            "沙中土": cls.SHA_ZHONG_TU,
            "天上火": cls.TIAN_SHANG_HUO,
            "石榴木": cls.SHI_LIU_MU,
            "大海水": cls.DA_HAI_SHUI,
        }
        return mapping[name.strip()]


class DiShi(Enum):
    CHANGSHENG = "CHANGSHENG"
    MUYU = "MUYU"
    GUANDAI = "GUANDAI"
    LINGUAN = "LINGUAN"
    DIWANG = "DIWANG"
    SHUAI = "SHUAI"
    BING = "BING"
    SI = "SI"
    MU = "MU"
    JUE = "JUE"
    TAI = "TAI"
    YANG = "YANG"

    @classmethod
    def from_chinese_name(cls, name: str) -> "DiShi":
        mapping = {
            "长生": cls.CHANGSHENG,
            "沐浴": cls.MUYU,
            "冠带": cls.GUANDAI,
            "临官": cls.LINGUAN,
            "帝旺": cls.DIWANG,
            "衰": cls.SHUAI,
            "病": cls.BING,
            "死": cls.SI,
            "墓": cls.MU,
            "绝": cls.JUE,
            "胎": cls.TAI,
            "养": cls.YANG,
        }
        return mapping[name.strip()]


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

    @classmethod
    def from_chinese_name(cls, name: str) -> "Shishen":
        mapping = {
            "日主": cls.RIZHU,
            "比肩": cls.BIJIAN,
            "劫财": cls.JIECAI,
            "食神": cls.SHISHEN,
            "伤官": cls.SHANGGUAN,
            "偏财": cls.PIANCAI,
            "正财": cls.ZHENGCAI,
            "七杀": cls.QISHA,
            "正官": cls.ZHENGGUAN,
            "偏印": cls.PIANYIN,
            "正印": cls.ZHENGYIN,
        }
        return mapping[name.strip()]

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


def get_shishen_enum_by_chinese(shishen_name: str) -> Shishen:
    # 兼容旧调用：推荐直接使用 Shishen.from_chinese_name(...)
    return Shishen.from_chinese_name(shishen_name)


def get_wuxing_enum_by_chinese(wuxing_name: str) -> Wuxing:
    mapping = {
        "木": Wuxing.MU,
        "火": Wuxing.HUO,
        "土": Wuxing.TU,
        "金": Wuxing.JIN,
        "水": Wuxing.SHUI,
    }
    return mapping[wuxing_name]
