# analysis/shishen/shishen_analyser.py

import copy
from typing import List, Tuple, Dict, Any

from ..base_analyser import BaseAnalyser
from ...core import (
    Clue, Shishen, Gan, Zhi, Yinyang, Area, Condition,
    GejuEnum,
    get_tiangandizhi_state, get_shishen_gan
)
from ...core.bazi_chart import BaziChart
from ...utils import LogHelper


class ShishenClue(Clue):
    def __init__(self, area: Area, content: str, shishen: Shishen, condition: Condition, reason: str):
        super().__init__(area, content, reason)
        self._shishen: Shishen = shishen.chinese_name
        self.condition: Condition = condition

    def __repr__(self) -> str:
        return f"{self.area.value}: 情形: {self.reason}； 影响：{self.content} (十神: {self._shishen})"

class ShishenAnalyser(BaseAnalyser):
    def __init__(
        self,
        bazi_chart: BaziChart,
        log_helper: LogHelper,
        hehua_analysis_results: Dict[str, Any],
        xinghai_results: Dict[str, Any],
        shensha_results: List[Dict[str, Any]],
        geju_analysis_results: List[GejuEnum],
        power_results
    ):
        super().__init__(bazi_chart, log_helper)
        self._hehua_analysis_results: Dict[str, Any] = hehua_analysis_results
        self._xinghai_results: Dict[str, Any] = xinghai_results
        self._shensha_results: List[Dict[str, Any]] = shensha_results
        self._geju_analysis_results: List[GejuEnum] = geju_analysis_results
        self._power_results = power_results
        self._clues: List[ShishenClue] = []
        self._updated_gan_shishen_list: List = []
        self._updated_zhi_hidden_gans_shishen_list: List[List[Shishen]] = []
        self._conflict_present: bool = False
        self.zhu_length = 3 if self._bazi_chart.without_time else 4

        # 初始化十神数量统计变量
        self._zhengguan_gan_count = 0
        self._zhengguan_zhi_count = 0
        self._zhengguan_zhi_benqi_count = 0
        self._qisha_gan_count = 0
        self._qisha_zhi_count = 0
        self._qisha_zhi_benqi_count = 0
        self._bijian_gan_count = 0
        self._bijian_zhi_count = 0
        self._bijian_zhi_benqi_count = 0
        self._jiecai_gan_count = 0
        self._jiecai_zhi_count = 0
        self._jiecai_zhi_benqi_count = 0
        self._zhengyin_gan_count = 0
        self._zhengyin_zhi_count = 0
        self._zhengyin_zhi_benqi_count = 0
        self._pianyin_gan_count = 0
        self._pianyin_zhi_count = 0
        self._pianyin_zhi_benqi_count = 0
        self._piancai_gan_count = 0
        self._piancai_zhi_count = 0
        self._piancai_zhi_benqi_count = 0
        self._zhengcai_gan_count = 0
        self._zhengcai_zhi_count = 0
        self._zhengcai_zhi_benqi_count = 0
        self._shangguan_gan_count = 0
        self._shangguan_zhi_count = 0
        self._shangguan_zhi_benqi_count = 0
        self._shishen_gan_count = 0
        self._shishen_zhi_count = 0
        self._shishen_zhi_benqi_count = 0

    def analyse(self) -> List[ShishenClue]:
        self._log_helper.info("【十神定位分析】\n")
        self._update_shishen_for_multi_occurrences()
        self._conflict_present = any(
            self._is_chong_present(idx) or self._is_sanxing_present(idx) or self._is_xiangxing_present(idx)
            for idx in range(self.zhu_length)
        )
        # 统计十神数量
        self._count_shishen_numbers()
        self._log_helper.debug("十神数量统计完成。\n")

        # 分析各个十神
        self._analyse_bijian()
        self._analyse_jiecai()
        self._analyse_pianyin()
        self._analyse_zhengyin()
        self._analyse_piancai()
        self._analyse_zhengcai()
        self._analyse_zhengguan()
        self._analyse_qisha()
        self._analyse_shishen()
        self._analyse_shangguan()

        self._log_helper.debug("十神定位分析完成。\n")

        # 输出所有线索
        for clue in self._clues:
            self._log_helper.info(f"{clue}\n")

        return self._clues

    def _count_shishen_numbers(self) -> None:
        # 使用 _count_shishen 方法统计每个十神的数量
        self._zhengguan_gan_count, self._zhengguan_zhi_count, self._zhengguan_zhi_benqi_count = self._count_shishen(Shishen.ZHENGGUAN)
        self._qisha_gan_count, self._qisha_zhi_count, self._qisha_zhi_benqi_count = self._count_shishen(Shishen.QISHA)
        self._bijian_gan_count, self._bijian_zhi_count, self._bijian_zhi_benqi_count = self._count_shishen(Shishen.BIJIAN)
        self._jiecai_gan_count, self._jiecai_zhi_count, self._jiecai_zhi_benqi_count = self._count_shishen(Shishen.JIECAI)
        self._zhengyin_gan_count, self._zhengyin_zhi_count, self._zhengyin_zhi_benqi_count = self._count_shishen(Shishen.ZHENGYIN)
        self._pianyin_gan_count, self._pianyin_zhi_count, self._pianyin_zhi_benqi_count = self._count_shishen(Shishen.PIANYIN)
        self._piancai_gan_count, self._piancai_zhi_count, self._piancai_zhi_benqi_count = self._count_shishen(Shishen.PIANCAI)
        self._zhengcai_gan_count, self._zhengcai_zhi_count, self._zhengcai_zhi_benqi_count = self._count_shishen(Shishen.ZHENGCAI)
        self._shangguan_gan_count, self._shangguan_zhi_count, self._shangguan_zhi_benqi_count = self._count_shishen(Shishen.SHANGGUAN)
        self._shishen_gan_count, self._shishen_zhi_count, self._shishen_zhi_benqi_count = self._count_shishen(Shishen.SHISHEN)

    def _update_shishen_for_multi_occurrences(self) -> None:
        # 深复制原始列表以避免修改原始数据
        self._updated_gan_shishen_list = copy.deepcopy(self._bazi_chart.gan_shishen_list)
        self._updated_zhi_hidden_gans_shishen_list = copy.deepcopy(self._bazi_chart.zhi_hidden_gans_shishen_list)

        # 影响到的十神以及它们对应变化的十神
        affected_shishens: Dict[Shishen, Shishen] = {
            Shishen.ZHENGGUAN: Shishen.QISHA,
            Shishen.ZHENGYIN: Shishen.PIANYIN,
            Shishen.SHISHEN: Shishen.SHANGGUAN
        }

        # 计算各受影响十神出现次数
        for shishen, new_shishen in affected_shishens.items():
            # 统计天干中该十神的出现次数
            gan_count = sum(1 for ss in self._updated_gan_shishen_list if ss == shishen)

            # 统计地支藏干中该十神的出现次数
            zhi_count = sum(1 for zhi_shishen_list in self._updated_zhi_hidden_gans_shishen_list for ss in zhi_shishen_list if ss == shishen)

            # 总出现次数
            total_count = gan_count + zhi_count

            # 如果总出现次数大于3，且天干和地支中均有出现，则执行替换
            if total_count > 3 and gan_count > 0 and zhi_count > 0:
                self._log_helper.info(f"{shishen.chinese_name}多见，视同为{new_shishen.chinese_name}\n")

                # 更新天干中的十神
                for i in range(self.zhu_length):
                    if self._updated_gan_shishen_list[i] == shishen:
                        self._updated_gan_shishen_list[i] = new_shishen

                # 更新地支藏干中的十神（只修改第一藏干）
                for i in range(self.zhu_length):
                    if self._updated_zhi_hidden_gans_shishen_list[i][0] == shishen:
                        self._updated_zhi_hidden_gans_shishen_list[i][0] = new_shishen

    def _add_clue(self, clue: ShishenClue) -> None:
        self._clues.append(clue)
        self._log_helper.debug(f"添加线索：{clue}")


    def _count_shishen(self, shishen: Shishen) -> Tuple[int, int, int]:
        gan_count = sum(1 for ss in self._updated_gan_shishen_list if ss == shishen)
        zhi_count = sum(1 for hidden_gans in self._updated_zhi_hidden_gans_shishen_list for ss in hidden_gans if ss == shishen)
        zhi_benqi_count = sum(1 for hidden_gans in self._updated_zhi_hidden_gans_shishen_list if hidden_gans[0] == shishen)
        return gan_count, zhi_count, zhi_benqi_count

    def _is_shensha_present(self, shensha_name, position):
        for item in self._shensha_results:
            if item['name'] == shensha_name and item['position'] == self._bazi_chart.zhu_list[position]:
                return True
        return False

    def _is_shensha_present_all(self, shensha_name):
        for position in range(self.zhu_length):
            if self._is_shensha_present(shensha_name, position):
                return True
        return False

    def _is_sanxing_present(self, position):
        sanxing_patterns = [("寅", "巳", "申"), ("丑", "戌", "未")]
        for pattern in sanxing_patterns:
            positions = self._xinghai_results.get("刑", {}).get(pattern, [])
            if position in positions:
                return True
        return False

    def _is_xiangxing_present(self, position):
        xiangxing_patterns = [("子", "卯"), ("子", "午"), ("子", "未"), ("丑", "午"), ("寅", "巳"), ("卯", "辰"), ("申", "亥"), ("酉", "戌")]
        for pattern in xiangxing_patterns:
            positions = self._xinghai_results.get("刑", {}).get(pattern, [])
            if position in positions:
                return True
        return False

    def _is_chong_present(self, position):
        chong_results = self._hehua_analysis_results.get("地支六冲", [])
        for item in chong_results:
            if position in item.idx_list:
                return True
        return False

    def _is_sanhui_present(self, position):
        sanhui_results = self._hehua_analysis_results.get("地支三会", [])
        for item in sanhui_results:
            if position in item.idx_list:
                return True
        return False

    def _is_sanhe_present(self, position):
        sanhe_results = self._hehua_analysis_results.get("地支三合", [])
        for item in sanhe_results:
            if position in item.idx_list:
                return True
        return False

    def _is_liuhe_present(self, position):
        liuhe_results = self._hehua_analysis_results.get("地支六合", [])
        for item in liuhe_results:
            if position in item.idx_list:
                return True
        return False

    def _is_wuhe_present(self, position):
        count = 0
        wuhe_results = self._hehua_analysis_results.get("天干五合", [])
        for item in wuhe_results:
            if position in item.idx_list:
                count += 1
        return count

    def _is_zuozhuanwei_shishen(self, hidden_gans_shishen, shishen):
        return len(hidden_gans_shishen) == 1 and hidden_gans_shishen[0] == shishen

    def _is_over(self, shishen: Shishen) -> bool:
        mapping = {
            Shishen.ZHENGGUAN: [self._zhengguan_gan_count, self._zhengguan_zhi_count, self._zhengguan_zhi_benqi_count],
            Shishen.QISHA: [self._qisha_gan_count, self._qisha_zhi_count, self._qisha_zhi_benqi_count],
            Shishen.BIJIAN: [self._bijian_gan_count, self._bijian_zhi_count, self._bijian_zhi_benqi_count],
            Shishen.JIECAI: [self._jiecai_gan_count, self._jiecai_zhi_count, self._jiecai_zhi_benqi_count],
            Shishen.ZHENGYIN: [self._zhengyin_gan_count, self._zhengyin_zhi_count, self._zhengyin_zhi_benqi_count],
            Shishen.PIANYIN: [self._pianyin_gan_count, self._pianyin_zhi_count, self._pianyin_zhi_benqi_count],
            Shishen.PIANCAI: [self._piancai_gan_count, self._piancai_zhi_count, self._piancai_zhi_benqi_count],
            Shishen.ZHENGCAI: [self._zhengcai_gan_count, self._zhengcai_zhi_count, self._zhengcai_zhi_benqi_count],
            Shishen.SHANGGUAN: [self._shangguan_gan_count, self._shangguan_zhi_count, self._shangguan_zhi_benqi_count],
            Shishen.SHISHEN: [self._shishen_gan_count, self._shishen_zhi_count, self._shishen_zhi_benqi_count]
        }
        gan_count, zhi_count, zhi_benqi_count = mapping[shishen]
        return (gan_count > 0 and zhi_benqi_count > 0) or (gan_count > 0 and zhi_count > 1) or self._jiecai_gan_count == 3 or zhi_benqi_count > 2

    def _analyse_bijian(self):
        self._log_helper.debug("分析比肩...")
        # 检查比肩过多
        total_bijian = self._bijian_gan_count + self._bijian_zhi_count + self._jiecai_gan_count + self._jiecai_zhi_count
        total_zhengguan_qisha = self._zhengguan_gan_count + self._zhengguan_zhi_count + self._qisha_gan_count + self._qisha_zhi_count

        if self._is_over(Shishen.BIJIAN):
            if total_bijian > total_zhengguan_qisha:
                self._add_clue(ShishenClue(Area.CHARACTER, "性情急躁", Shishen.BIJIAN, Condition.EXCESS, '比肩过多'))
                self._add_clue(ShishenClue(Area.FAMILY, "兄弟相互之间，缺乏相助之兆，好友知交相处不会太久", Shishen.BIJIAN, Condition.EXCESS, '比肩过多'))
                self._add_clue(ShishenClue(Area.LOVE, "夫妻时有两不和谐", Shishen.BIJIAN, Condition.EXCESS, '比肩过多'))
                self._add_clue(ShishenClue(Area.CAREER, "即使是成了美好格局，亦是劳碌命，凡事不放心，事必躬亲", Shishen.BIJIAN, Condition.EXCESS, '比肩过多'))
                self._add_clue(ShishenClue(Area.LOVE, "感情过程，多有波折", Shishen.BIJIAN, Condition.EXCESS, '比肩过多'))
                self._add_clue(ShishenClue(Area.SOCIAL, "有不好意思拒绝他人的麻烦", Shishen.BIJIAN, Condition.EXCESS, '比肩过多'))
                self._add_clue(ShishenClue(Area.CHARACTER, "因累积之情绪，会有突发性之过急，与轻率放弃之弊", Shishen.BIJIAN, Condition.EXCESS, '比肩过多'))
                self._add_clue(ShishenClue(Area.CHARACTER, "对人比较少警戒防范之心，易于乐天知命", Shishen.BIJIAN, Condition.EXCESS, '比肩过多'))
                
                if self._bijian_gan_count >= 2:
                    self._add_clue(ShishenClue(Area.CHARACTER, "言谈多涉善意之题外话，不易守密", Shishen.BIJIAN, Condition.EXCESS, "天干有至少二个比肩"))
                
                if total_zhengguan_qisha == 0:
                    self._add_clue(ShishenClue(Area.CHARACTER, "性情急躁", Shishen.BIJIAN, Condition.EXCESS, "比肩多而四柱无正官七杀"))

        # 检查空亡、羊刃、三刑、冲
        for position, shishen in enumerate(self._updated_gan_shishen_list):
            gan = self._bazi_chart.gan_list[position]._gan
            if shishen == Shishen.BIJIAN:
                # 空亡
                if self._is_shensha_present("Kongwang", position):
                    self._add_clue(ShishenClue(Area.CHARACTER, "不利父与妻子", Shishen.BIJIAN, Condition.SITTING_ON_EMPTY, "比肩坐空亡"))

                # 羊刃
                if self._is_shensha_present("Yangren", position):
                    self._add_clue(ShishenClue(Area.CHARACTER, "父先亡", Shishen.BIJIAN, Condition.SITTING_ON_YANGREN, "比肩坐羊刃"))

                # 三刑
                if self._is_sanxing_present(position):
                    self._add_clue(ShishenClue(Area.CHARACTER, "幼年艰困，白手自立", Shishen.BIJIAN, Condition.SITTING_ON_SANXING, "比肩地支通三刑"))

                # 冲
                if self._is_chong_present( position):
                    self._add_clue(ShishenClue(Area.CHARACTER, "兄弟手足和谐", Shishen.BIJIAN, Condition.SITTING_ON_CHONG, "比肩地支遇冲"))

                # 绝
                zhi = self._bazi_chart.get_zhi_by_index(position)
                if gan not in {Gan.WU, Gan.JI, Gan.REN, Gan.GUI} and get_tiangandizhi_state(gan, "绝") == zhi:
                    self._add_clue(ShishenClue(Area.FAMILY, "主兄弟极少，或者是兄弟很少谋面之兆", Shishen.BIJIAN, Condition.SITTING_ON_JUE, "比肩坐绝"))
    
    def _analyse_jiecai(self):
        self._log_helper.debug("分析劫财...")
        # 条件1: 检查劫财多

        if self._is_over(Shishen.JIECAI):
            self._add_clue(ShishenClue(Area.CHARACTER, "谦虚之中，带有骄气", Shishen.JIECAI, Condition.EXCESS, "劫财过多"))
            self._add_clue(ShishenClue(Area.CHARACTER, "凡事先理情,而后情理", Shishen.JIECAI, Condition.EXCESS, "劫财过多"))
            self._add_clue(ShishenClue(Area.CHARACTER, "先细节,而后论全局", Shishen.JIECAI, Condition.EXCESS, "劫财过多"))
            self._add_clue(ShishenClue(Area.CHARACTER, "一旦发生事端之事，有坚持到底的倾向", Shishen.JIECAI, Condition.EXCESS, "劫财过多"))
            self._add_clue(ShishenClue(Area.CHARACTER, "有相当程度的理想,但较乏协调之弹性", Shishen.JIECAI, Condition.EXCESS, "劫财过多"))
            self._add_clue(ShishenClue(Area.CHARACTER, "一旦发觉自己不利的环境;迅速而能改变自己的立场", Shishen.JIECAI, Condition.EXCESS, "劫财过多"))
            self._add_clue(ShishenClue(Area.SOCIAL, "不尚抽象性之空谈", Shishen.JIECAI, Condition.EXCESS, "劫财过多"))
            self._add_clue(ShishenClue(Area.SOCIAL, "不惧闲言闲语的干扰", Shishen.JIECAI, Condition.EXCESS, "劫财过多"))
            self._add_clue(ShishenClue(Area.SOCIAL, "重大之事贵备他人之时,往往不易顾及他人之面子是否难堪", Shishen.JIECAI, Condition.EXCESS, "劫财过多"))
            self._add_clue(ShishenClue(Area.LOVE, "夫妇都少有圆满之恩情", Shishen.JIECAI, Condition.EXCESS, "劫财过多"))
            self._add_clue(ShishenClue(Area.CAREER, "合作事业，俱为有始无终之结局", Shishen.JIECAI, Condition.EXCESS, "劫财过多"))

        # 条件2: 检查羊刃格，无七杀或食神格
        if (
            GejuEnum.YANGREN_GE in self._geju_analysis_results
            and GejuEnum.QISHA_GE not in self._geju_analysis_results
            and GejuEnum.SHISHEN_GE not in self._geju_analysis_results
        ):
            self._add_clue(ShishenClue(Area.LOVE, "婚姻不圆满", Shishen.JIECAI, Condition.MONTH_ZHI, "羊刃格成立，同时无七杀或食神格"))
            if self._bazi_chart.gender == 'female':
                self._add_clue(ShishenClue(Area.CHARACTER, "个性强，作事干练", Shishen.JIECAI, Condition.MONTH_ZHI, "女命羊刃格成立，同时无七杀或食神格"))

        # 1. 日主地支根坐专位劫财者
        if (self._bazi_chart.day_gan == Gan.REN and self._bazi_chart.day_zhi == Zhi.ZI) or (self._bazi_chart.day_gan == Gan.BING and self._bazi_chart.day_zhi == Zhi.WU):
            if self._jiecai_gan_count == 0 and not self._is_chong_present( 2) and not self._is_sanxing_present(2) and not self._is_xiangxing_present(2):
                self._add_clue(ShishenClue(Area.CHARACTER, "眼光高，独立性强。", Shishen.JIECAI, Condition.DAY_ZHI, "日主地支根坐专位劫财"))
                if self._bazi_chart.gender == 'female':
                    self._add_clue(ShishenClue(Area.LOVE, "通常迟婚，婚后有自己的事业或兼顾丈夫事业。", Shishen.JIECAI, Condition.DAY_ZHI, "女命日主地支根坐专位劫财"))

        # 2. 日主根坐劫财，羊刃透出天干
        if ((self._bazi_chart.day_gan == Gan.REN and self._bazi_chart.day_zhi == Zhi.ZI) or (self._bazi_chart.day_gan == Gan.BING and self._bazi_chart.day_zhi == Zhi.WU)) and self._jiecai_gan_count > 0:
            self._add_clue(ShishenClue(Area.LOVE, "夫妻互有苦情。", Shishen.JIECAI, Condition.DAY_ZHI, "日主根坐劫财，羊刃透出天干"))
            self._add_clue(ShishenClue(Area.FAMILY, "父早离。", Shishen.JIECAI, Condition.DAY_ZHI, "日主根坐劫财，羊刃透出天干"))
            if self._bazi_chart.gender == 'female':
                self._add_clue(ShishenClue(Area.LOVE, "夫妻财产明示各有范围。", Shishen.JIECAI, Condition.DAY_ZHI, "女命日主根坐劫财，羊刃透出天干"))
                self._add_clue(ShishenClue(Area.LOVE, "斤斤计较于小事，经常觉得对象处理错事。", Shishen.JIECAI, Condition.DAY_ZHI, "女命日主根坐劫财，羊刃透出天干"))
                self._add_clue(ShishenClue(Area.LOVE, "公有财产中自认为部分属于自己。", Shishen.JIECAI, Condition.DAY_ZHI, "女命日主根坐劫财，羊刃透出天干"))
                self._add_clue(ShishenClue(Area.LOVE, "经常独自决定一些对方不同意之事。", Shishen.JIECAI, Condition.DAY_ZHI, "女命日主根坐劫财，羊刃透出天干"))
                self._add_clue(ShishenClue(Area.LOVE, "老夫少妻或者双方身世有相当距离。", Shishen.JIECAI, Condition.DAY_ZHI, "女命日主根坐劫财，羊刃透出天干"))
                self._add_clue(ShishenClue(Area.LOVE, "整日忙于自己之事，忽略夫妻情趣。", Shishen.JIECAI, Condition.DAY_ZHI, "女命日主根坐劫财，羊刃透出天干"))
                self._add_clue(ShishenClue(Area.LOVE, "敢爱敢恨。", Shishen.JIECAI, Condition.DAY_ZHI, "女命日主根坐劫财，羊刃透出天干"))
            if self._bazi_chart.gender == 'male':
                self._add_clue(ShishenClue(Area.LOVE, "多主双妻之缘。", Shishen.JIECAI, Condition.DAY_ZHI, "男命日主根坐劫财，羊刃透出天干"))

        # 4. 同一柱中，劫财、伤官、羊刃全见，全局无七杀或食神格者
        for i in range(self.zhu_length):
            gan_shishen = self._updated_gan_shishen_list[i]
            zhi_hidden_gans_shishen = self._updated_zhi_hidden_gans_shishen_list[i]
            zhu_shishen = []
            zhu_shishen.append(gan_shishen)
            zhu_shishen += zhi_hidden_gans_shishen
            if set([Shishen.JIECAI, Shishen.SHANGGUAN]).issubset(set(zhu_shishen)) and self._is_shensha_present("Yangren", i):
                if self._qisha_gan_count == 0 and self._shishen_gan_count == 0:
                    self._add_clue(ShishenClue(Area.FORTUNE, "外表华美，内实拮据，屋富人贫，家庭生活寂寞。", Shishen.JIECAI, Condition.OTHER, "同一柱中，劫财、伤官、羊刃全见，全局无七杀或食神格"))
                    self._add_clue(ShishenClue(Area.LOVE, "姻缘易变，富而不持久，为金钱而引发是非祸端。", Shishen.JIECAI, Condition.OTHER, "同一柱中，劫财、伤官、羊刃全见，全局无七杀或食神格"))
                    if i == 0:
                        self._add_clue(ShishenClue(Area.FAMILY, "年柱：不利家长。", Shishen.JIECAI, Condition.YEAR_ZHI, "年柱，劫财、伤官、羊刃全见，全局无七杀或食神格"))
                    elif i == 1:
                        self._add_clue(ShishenClue(Area.LOVE, "月柱：不利婚姻。", Shishen.JIECAI, Condition.MONTH_ZHI, "月柱，劫财、伤官、羊刃全见，全局无七杀或食神格"))
                    elif i == 3 and not self._bazi_chart.without_time:
                        self._add_clue(ShishenClue(Area.CHILDREN, "时柱：不利子女。", Shishen.JIECAI, Condition.HOUR_ZHI, "时柱，劫财、伤官、羊刃全见，全局无七杀或食神格"))

    def _analyse_pianyin(self):
        self._log_helper.debug("分析偏印...")
        
        if self._is_over(Shishen.PIANYIN):
            # 性格方面
            self._add_clue(ShishenClue(Area.CHARACTER, "主性格孤僻，表达力失之于太含蓄，有些拗泥", Shishen.PIANYIN, Condition.EXCESS, "偏印过多"))
            self._add_clue(ShishenClue(Area.CHARACTER, "在感情之有椎心之压力与沈闷", Shishen.PIANYIN, Condition.EXCESS, "偏印过多"))
            self._add_clue(ShishenClue(Area.CHARACTER, "有时成一种提不起，放不下的患难包袱", Shishen.PIANYIN, Condition.EXCESS, "偏印过多"))
            self._add_clue(ShishenClue(Area.CHARACTER, "近似有些诉之于高尚动机的不肯认错", Shishen.PIANYIN, Condition.EXCESS, "偏印过多"))
            self._add_clue(ShishenClue(Area.CHARACTER, "凡事都是倾向于悲观的成份居多", Shishen.PIANYIN, Condition.EXCESS, "偏印过多"))
            if self._jiecai_gan_count == 0 and self._jiecai_zhi_count == 0:
                self._add_clue(ShishenClue(Area.CHARACTER, "性格消极,带自卑之心态", Shishen.PIANYIN, Condition.EXCESS, "偏印过多，没有劫财"))

            # 社交方面
            self._add_clue(ShishenClue(Area.SOCIAL, "遇事不称心之时,则出言简短而带语剌;格峻调孤", Shishen.PIANYIN, Condition.EXCESS, "偏印过多"))

            # 事业方面
            self._add_clue(ShishenClue(Area.CAREER, "做事有始无终,高雅式的固执。遇事先设想其过程的困难。善于发现事理之困难处,而不善面对困难之处理", Shishen.PIANYIN, Condition.EXCESS, "偏印过多"))

            # 爱情方面
            if self._bazi_chart.gender == 'female':
                self._add_clue(ShishenClue(Area.LOVE, "心事经常是不明白表示，要伴侣猜喜好", Shishen.PIANYIN, Condition.EXCESS, "女命偏印过多"))

            # 天赋方面
            self._add_clue(ShishenClue(Area.TALENT, "有艺术、文学，哲理之才赋。对宗教、音乐亦为适宜", Shishen.PIANYIN, Condition.EXCESS, "偏印过多"))

            # 名誉方面
            if not any(gan._yinyang == Yinyang.YANG for gan in self._bazi_chart.gan_list) and not any(gan.yinyang == Yinyang.YANG for zhi_hidden_gans in self._bazi_chart.zhi_hidden_gans_list for gan in zhi_hidden_gans):
                self._add_clue(ShishenClue(Area.REPUTATION, "恐有言清行浊之弊。", Shishen.PIANYIN, Condition.EXCESS, "偏印过多,四柱全阴"))
                if self._is_shensha_present_all('Hongyan') and self._bazi_chart.gender == "female":
                    self._add_clue(ShishenClue(Area.REPUTATION, "恐有失声誉。", Shishen.PIANYIN, Condition.EXCESS, "偏印过多,四柱全阴,带红艳煞"))

            # 家庭方面
            if self._bazi_chart.gender == 'female':
                self._add_clue(ShishenClue(Area.CHILDREN, "子息少，也不喜欢带小孩", Shishen.PIANYIN, Condition.EXCESS, "女命偏印过多"))

            # 偏印过多，又与伤官同时透出天干，若没有偏财且没有天月德贵人
            # 偏印过多，同时也有天、月德贵人，或者有偏财见于天干
            # 检查天月德贵人是否存在
            tiande_present = self._is_shensha_present_all('Tiandeguiren')
            yuede_present = self._is_shensha_present_all('Yuedeguiren')
            if self._shangguan_gan_count > 0 and self._piancai_gan_count == 0 and not (tiande_present and yuede_present):
                if self._bazi_chart.gender == 'female':
                    self._add_clue(ShishenClue(Area.LOVE, "不利婚姻", Shishen.PIANYIN, Condition.EXCESS, "偏印过多，又与伤官同时透出天干，没有偏财且没有天月德贵人"))
                    self._add_clue(ShishenClue(Area.CHILDREN, "不利子女", Shishen.PIANYIN, Condition.EXCESS, "偏印过多，又与伤官同时透出天干，没有偏财且没有天月德贵人"))

            if (tiande_present and yuede_present) or self._piancai_gan_count > 0:
                self._add_clue(ShishenClue(Area.CAREER, "艺术得贵人欣赏，自可鱼跃龙门", Shishen.PIANYIN, Condition.EXCESS, "偏印多，又与伤官同时透出天干，有偏财"))
            elif self._pianyin_zhi_count > 1:
                self._add_clue(ShishenClue(Area.FORTUNE, "智重福轻之人", Shishen.PIANYIN, Condition.EXCESS, "偏印多，又与伤官同时透出天干，有天月德贵人"))

        # 偏印在年柱，干支俱透，不利于长亲
        if self._updated_gan_shishen_list[0] == Shishen.PIANYIN and Shishen.PIANYIN in self._updated_zhi_hidden_gans_shishen_list[0]:
            self._add_clue(ShishenClue(Area.FAMILY, "不利于长亲", Shishen.PIANYIN, Condition.YEAR_ZHI, "偏印在年柱，干支俱透"))

        # 月干和月支第一个藏干十神均为偏印，且月支只有一个藏干
        if self._updated_gan_shishen_list[1] == Shishen.PIANYIN and self._is_zuozhuanwei_shishen(self._updated_zhi_hidden_gans_shishen_list[1], Shishen.PIANYIN):
            self._add_clue(ShishenClue(Area.CAREER, "以艺术、文学、技术、医学、玄学等专长为业", Shishen.PIANYIN, Condition.MONTH_ZHI, "月干和月支专位偏印"))
            self._add_clue(ShishenClue(Area.FORTUNE, "有慧福浅之人", Shishen.PIANYIN, Condition.MONTH_ZHI, "月干和月支专位偏印"))

        # 偏印坐在绝位，或遇天干坐绝且地支第一个藏干为偏印
        for i in range(self.zhu_length):
            gan = self._bazi_chart.gan_list[i]
            zhi = self._bazi_chart.zhi_list[i]
            gan_shishen = self._updated_gan_shishen_list[i]
            zhi_hidden_gans_shishen = self._updated_zhi_hidden_gans_shishen_list[i][0]  # 只考虑地支第一个藏干的十神

            # 检查地支是否是天干的绝位
            if get_tiangandizhi_state(gan, "绝") == zhi:
                # 判断天干的十神是否是偏印，以及地支的第一个藏干的十神是否是偏印
                if gan_shishen == Shishen.PIANYIN or zhi_hidden_gans_shishen == Shishen.PIANYIN:
                    self._add_clue(ShishenClue(Area.CAREER,  "纵有绝技在身，不易获得应有之代价，成就及声誉，经常是属于吃力不讨好的境地。", Shishen.PIANYIN, Condition.SITTING_ON_JUE, "偏印坐在绝位，或遇天干压偏印于绝"))

        # 日支坐偏印于专位，即是出生于丁卯日、癸酉日
        if (self._bazi_chart.day_gan == Gan.DING and self._bazi_chart.day_zhi == Zhi.MAO) or (self._bazi_chart.day_gan == Gan.GUI and self._bazi_chart.day_zhi == Zhi.YOU):
            self._add_clue(ShishenClue(Area.LOVE, "姻缘俱有苦衷", Shishen.PIANYIN, Condition.DAY_ZHI, "日支坐偏印于专位"))
            # 日支只有一个藏干且藏干为偏印，又遇冲刑者
            if self._is_sanxing_present(2) or self._is_chong_present( 2) or self._is_xiangxing_present(2):
                self._add_clue(ShishenClue(Area.FORTUNE, "因自己的性格而惹祸招争难", Shishen.PIANYIN, Condition.DAY_ZHI, "日支坐偏印于专位，又遇冲刑"))

        # 天干二见偏印，甚或者是三见偏印者，皆主迟婚、变缘、独身之兆
        if self._pianyin_gan_count >= 2:
            self._add_clue(ShishenClue(Area.LOVE, "主迟婚、变缘、独身之兆", Shishen.PIANYIN, Condition.EXCESS, "天干至少二见偏印"))

    def _analyse_zhengyin(self):
        self._log_helper.debug("分析正印...")

        if self._is_over(Shishen.ZHENGYIN):
            # 性格方面
            self._add_clue(ShishenClue(Area.CHARACTER, "为人聪明有谋，善于隐藏自己心中真正的目的。看情形而表达，是属于善体人意的智慧人士。即使遇到不如意的遭遇与处境，也能顺应外界的客观形势。是一种典型的识时务者为俊杰。主秀气、塾术、文才之气。", Shishen.ZHENGYIN, Condition.EXCESS, "正印过多"))
            self._add_clue(ShishenClue(Area.FORTUNE, "理财保守。", Shishen.ZHENGYIN, Condition.EXCESS, "正印过多"))
            self._add_clue(ShishenClue(Area.SOCIAL, "不太多无谓之人情，遇事之际，经常抱有得予人方便且方便，只要不拖累自己，处于厚道与自保之间。", Shishen.ZHENGYIN, Condition.EXCESS, "正印过多"))

            # 与正官或七杀同时存在
            if self._zhengguan_gan_count > 0 or self._qisha_gan_count > 0:
                self._add_clue(ShishenClue(Area.FORTUNE, "吉，有福业。", Shishen.ZHENGYIN, Condition.EXCESS, "正印过多与正官或七杀同时透出天干"))
            else:
                self._add_clue(ShishenClue(Area.CHARACTER, "为人礼貌保守本份。谦和中有修养，和光同尘，出辞温和。", Shishen.ZHENGYIN, Condition.EXCESS, "正印过多，正官或七杀都没有透出天干"))
                self._add_clue(ShishenClue(Area.CAREER, "不轻易改弦更张，很少改行。", Shishen.ZHENGYIN, Condition.EXCESS, "正印过多，正官或七杀都没有透出天干"))

            # 日主在地支之中有临官、帝旺之根
            day_gan = self._bazi_chart.day_gan
            if any(get_tiangandizhi_state(day_gan, state) in self._bazi_chart.zhi_list for state in ["临官", "帝旺"]):
                self._add_clue(ShishenClue(Area.CHARACTER, "孤寂", Shishen.ZHENGYIN, Condition.DAY_ZHI, "日主在地支之中有临官、帝旺之根"))
                self._add_clue(ShishenClue(Area.FORTUNE, "不善理财", Shishen.ZHENGYIN, Condition.DAY_ZHI, "日主在地支之中有临官、帝旺之根"))

        # 正印在年柱或月柱上，自坐死绝或地支有冲刑
        for i in range(2):
            shishen = self._updated_gan_shishen_list[i]
            gan = self._bazi_chart.gan_list[i]._gan
            if shishen == Shishen.ZHENGYIN:
                zhi = self._bazi_chart.zhi_list[i]
                if get_tiangandizhi_state(gan, "死") == zhi or get_tiangandizhi_state(gan, "绝") == zhi or self._conflict_present:
                    self._add_clue(ShishenClue(Area.FAMILY, "自坐死绝或地支有冲刑，不利于母亲。", Shishen.ZHENGYIN, Condition.OTHER, "正印在年柱或月柱上"))

        # 正印透出天干，与财星关系
        if self._zhengyin_gan_count > 0:
            if self._zhengcai_gan_count > 0 or self._piancai_gan_count > 0:
                # 先找到所有正印和财星的天干位置
                zhengyin_positions = [i for i, shishen in enumerate(self._updated_gan_shishen_list) if shishen == Shishen.ZHENGYIN]
                caixing_positions = [i for i, shishen in enumerate(self._updated_gan_shishen_list) if shishen in (Shishen.ZHENGCAI, Shishen.PIANCAI)]
                # a. 所有财星索引都小于所有正印索引，且无冲刑
                if all(cai < min(zhengyin_positions) for cai in caixing_positions) and not self._conflict_present:
                    self._add_clue(ShishenClue(Area.FORTUNE, "一生吉祥，多享现成之福业。", Shishen.ZHENGYIN, Condition.EXCESS, "先财后印"))
                # b. 所有财星索引都大于所有正印索引，适用于男命
                if all(cai > max(zhengyin_positions) for cai in caixing_positions) and self._bazi_chart.gender == 'male':
                    self._add_clue(ShishenClue(Area.CAREER, "平生多为他人奔忙。", Shishen.ZHENGYIN, Condition.EXCESS, "男命先印后财"))

        # 正印坐正财
        for i, shishen in enumerate(self._updated_gan_shishen_list):
            if shishen == Shishen.ZHENGYIN and self._is_zuozhuanwei_shishen(self._updated_zhi_hidden_gans_shishen_list[i], Shishen.ZHENGCAI):
                if self._bazi_chart.gender == 'male':
                    self._add_clue(ShishenClue(Area.LOVE, "正印坐正财：夫妻易伤。", Shishen.ZHENGYIN, Condition.OTHER, "男命正印坐正财"))

        # 正印坐专位正印
        for i, shishen in enumerate(self._updated_gan_shishen_list):
            if shishen == Shishen.ZHENGYIN and self._is_zuozhuanwei_shishen(self._updated_zhi_hidden_gans_shishen_list[i], Shishen.ZHENGYIN):
                self._add_clue(ShishenClue(Area.CHARACTER, "则过于自信。", Shishen.ZHENGYIN, Condition.OTHER, "正印坐专位正印"))
                self._add_clue(ShishenClue(Area.FAMILY, "母亲长寿。", Shishen.ZHENGYIN, Condition.OTHER, "正印坐专位正印"))
                if self._bazi_chart.gender == 'female':
                    self._add_clue(ShishenClue(Area.CHILDREN, "得孩子迟，头胎容易流产。", Shishen.ZHENGYIN, Condition.OTHER, "女命正印坐专位正印"))
                if i == 1:
                    self._add_clue(ShishenClue(Area.CAREER, "以艺文视作一种商品。视谦虚礼貌是人生成功的一种阶梯，重视实际，不尚浮谈。提得起，放得下。", Shishen.ZHENGYIN, Condition.MONTH_ZHI, "在月柱正印坐专位正印"))
                if self._zhengguan_gan_count == 0 and self._qisha_gan_count == 0:
                    if self._bazi_chart.gender == 'female':
                        self._add_clue(ShishenClue(Area.LOVE, "无良缘。", Shishen.ZHENGYIN, Condition.EXCESS, "女命正印坐专位正印，没有正官、七杀"))
                    else:
                        self._add_clue(ShishenClue(Area.CAREER, "男命以高级艺术为工作，从商则孤僻不聚财。", Shishen.ZHENGYIN, Condition.EXCESS, "男命正印坐专位正印，没有正官、七杀"))

        # 正印坐专位偏印
        for i, shishen in enumerate(self._updated_gan_shishen_list):
            if shishen == Shishen.ZHENGYIN and self._is_zuozhuanwei_shishen(self._updated_zhi_hidden_gans_shishen_list[i], Shishen.PIANYIN):
                self._add_clue(ShishenClue(Area.CAREER, "职业多有兼取，主业带副业的现象。", Shishen.ZHENGYIN, Condition.OTHER, "正印坐专位偏印"))
                self._add_clue(ShishenClue(Area.FAMILY, "另一半有健康问题，或有特别之嗜好。", Shishen.ZHENGYIN, Condition.OTHER, "正印坐专位偏印"))
                self._add_clue(ShishenClue(Area.CHILDREN, "得孩子迟。", Shishen.ZHENGYIN, Condition.OTHER, "正印坐专位偏印"))
                self._add_clue(ShishenClue(Area.WEALTH, "财务状况具备双重性，明的一个行业暗的一个行业。", Shishen.ZHENGYIN, Condition.OTHER, "正印坐专位偏印"))
                if self._bazi_chart.gender == 'female':
                    self._add_clue(ShishenClue(Area.CHARACTER, "性格不稳定，今天否定昨天的观点。", Shishen.ZHENGYIN, Condition.OTHER, "女命正印坐专位偏印"))

        # 正印坐专位伤官
        for i, shishen in enumerate(self._updated_gan_shishen_list):
            if shishen == Shishen.ZHENGYIN and self._is_zuozhuanwei_shishen(self._updated_zhi_hidden_gans_shishen_list[i], Shishen.SHANGGUAN):
                self._add_clue(ShishenClue(Area.CAREER, "只宜从事清高之事业。", Shishen.ZHENGYIN, Condition.OTHER, "正印坐专位伤官"))
                if self._bazi_chart.gender == 'female':
                    self._add_clue(ShishenClue(Area.LOVE, "婚姻有阻。", Shishen.ZHENGYIN, Condition.OTHER, "女命正印坐专位伤官"))

        # 正印坐羊刃
        for i, shishen in enumerate(self._updated_gan_shishen_list):
            if shishen == Shishen.ZHENGYIN and self._is_shensha_present("Yangren", i):
                self._add_clue(ShishenClue(Area.CAREER, "工作中身心多伤，心疲力竭。", Shishen.ZHENGYIN, Condition.OTHER, "正印坐羊刃"))

        # 正印、七杀、羊刃全者
        if self._zhengyin_gan_count > 0 and self._qisha_gan_count > 0 and self._is_shensha_present_all("Yangren"):
            if self._bazi_chart.gender == 'female':
                self._add_clue(ShishenClue(Area.CHARACTER, "自视甚高。矫情傲物。", Shishen.ZHENGYIN, Condition.EXCESS, "女命正印、七杀、羊刃全"))
                self._add_clue(ShishenClue(Area.HEALTH, "女命：身体恐有隐疾。", Shishen.ZHENGYIN, Condition.EXCESS, "女命正印、七杀、羊刃全"))
                self._add_clue(ShishenClue(Area.CHARACTER, "女命：性格偏狭，缺乏应有之耐心。", Shishen.ZHENGYIN, Condition.EXCESS, "女命正印、七杀、羊刃全"))
            else:
                self._add_clue(ShishenClue(Area.CHARACTER, "男命：能善陈条理，而少实质上的经验。", Shishen.ZHENGYIN, Condition.EXCESS, "男命正印、七杀、羊刃全"))
                self._add_clue(ShishenClue(Area.SOCIAL, "男命：有自居清高的倾向，不喜与志不同、道不合的人相处。", Shishen.ZHENGYIN, Condition.EXCESS, "男命正印、七杀、羊刃全"))
                self._add_clue(ShishenClue(Area.CHARACTER, "男命：心思精微，亦以相同之心态求他人，则近挑剔。", Shishen.ZHENGYIN, Condition.EXCESS, "男命正印、七杀、羊刃全"))
                self._add_clue(ShishenClue(Area.HEALTH, "男命：经常有小疾缠身。", Shishen.ZHENGYIN, Condition.EXCESS, "男命正印、七杀、羊刃全"))
                self._add_clue(ShishenClue(Area.LOVE, "男命：婚姻不佳。恐有非婚生子女。", Shishen.ZHENGYIN, Condition.EXCESS, "男命正印、七杀、羊刃全"))

    def _analyse_piancai(self):
        self._log_helper.debug("分析偏财...")

        if self._is_over(Shishen.PIANCAI):
            self._add_clue(ShishenClue(Area.CHARACTER, "不斤斤计较于小节，只在大处着眼；不喜在小事上讨价还价。", Shishen.PIANCAI, Condition.EXCESS, "偏财过多"))
            self._add_clue(ShishenClue(Area.CHARACTER, "性宽宏，有一种输得起、赢得起的性格，不会略见吃亏、损耗，就勃然变色。", Shishen.PIANCAI, Condition.EXCESS, "偏财过多"))
            self._add_clue(ShishenClue(Area.CHARACTER, "有时效上的观念，有重点式的迅、捷、敏的能力；但却不能持久。", Shishen.PIANCAI, Condition.EXCESS, "偏财过多"))
            self._add_clue(ShishenClue(Area.CHARACTER, "生活比较自由开放，不拘小节，多少有些异性朋友围绕。", Shishen.PIANCAI, Condition.EXCESS, "偏财过多"))
            self._add_clue(ShishenClue(Area.SOCIAL, "肯相助于人，其相助之条件，只不过是以他自己对此人之喜好与否而定。", Shishen.PIANCAI, Condition.EXCESS, "偏财过多"))
            self._add_clue(ShishenClue(Area.SOCIAL, "言辞虽很明朗，但由于天性乐观，在别人听来，多少有些夸张、草率，甚或视之为不负责之诈言。", Shishen.PIANCAI, Condition.EXCESS, "偏财过多"))
            self._add_clue(ShishenClue(Area.CHARACTER, "生活习惯，不经常按照一般的八小时制，有时会晨昏颠倒。", Shishen.PIANCAI, Condition.EXCESS, "偏财过多"))
            self._add_clue(ShishenClue(Area.CAREER, "商场弹性极强，即使是曾遭破产三五次，仍有东山再起之信心与勇气。", Shishen.PIANCAI, Condition.EXCESS, "偏财过多"))
            self._add_clue(ShishenClue(Area.CAREER, "善于应用机会、心理、形势等生财。", Shishen.PIANCAI, Condition.EXCESS, "偏财过多"))
            self._add_clue(ShishenClue(Area.CAREER, "有国际商业精神；自己有了利益，总会想到别人。", Shishen.PIANCAI, Condition.EXCESS, "偏财过多"))
            self._add_clue(ShishenClue(Area.SOCIAL, "有容易接受他人奉承的倾向，而故示大方。", Shishen.PIANCAI, Condition.EXCESS, "偏财过多"))
            self._add_clue(ShishenClue(Area.SOCIAL, "与异性谈话，常有一种很自然的半真半假，亦真亦假的神态。不露急的神态，不会斤斤计较，易于得异性之欢心。", Shishen.PIANCAI, Condition.EXCESS, "偏财过多"))
            self._add_clue(ShishenClue(Area.SOCIAL, "小事绝少失信，大事则看情形而定。", Shishen.PIANCAI, Condition.EXCESS, "偏财过多"))
            self._add_clue(ShishenClue(Area.CHARACTER, "平时不会露出寒酸拮据相。一旦破产事件发生，少有单独事件，而是一连串之事故。", Shishen.PIANCAI, Condition.EXCESS, "偏财过多"))
            self._add_clue(ShishenClue(Area.FORTUNE, "不论实际环境如何，衣食均为超过常人之上。是属于有口福、懂做人的一种。", Shishen.PIANCAI, Condition.EXCESS, "偏财过多"))
            if self._bazi_chart.gender == 'female':
                if self._bazi_chart.year_gan_shishen == Shishen.PIANCAI or self._bazi_chart.month_gan_shishen == Shishen.PIANCAI:
                    self._add_clue(ShishenClue(Area.FAMILY, "偏财透在年月：为孝女，听父亲的语。婚嫁之事，不会有逆父亲之意见。即使结婚以后，仍操心原生家庭。", Shishen.PIANCAI, Condition.EXCESS, "女命偏财过多"))
                if not self._bazi_chart.without_time and self._bazi_chart.hour_gan_shishen == Shishen.PIANCAI:
                    self._add_clue(ShishenClue(Area.FORTUNE, "偏财透在时：善理财，中年以后必有自己的事业。", Shishen.PIANCAI, Condition.EXCESS, "女命偏财过多"))

        # 偏财天透地藏年柱
        if self._bazi_chart.year_gan_shishen == Shishen.PIANCAI and Shishen.PIANCAI in self._updated_zhi_hidden_gans_shishen_list[0]:
            self._add_clue(ShishenClue(Area.FORTUNE, "主家世良好，且能得继承产业。", Shishen.PIANCAI, Condition.YEAR_ZHU, "偏财在年柱天透地藏"))

        # 偏财坐专位羊刃、劫财
        for i, shishen in enumerate(self._updated_gan_shishen_list):
            if shishen == Shishen.PIANCAI and (self._is_zuozhuanwei_shishen(self._updated_zhi_hidden_gans_shishen_list[i], Shishen.JIECAI) or self._is_shensha_present("Yangren", i)):
                self._add_clue(ShishenClue(Area.FAMILY, "父去他乡。", Shishen.PIANCAI, Condition.SITTING_ON_YANGREN, "偏财坐专位羊刃或劫财"))

        # 偏财透干，四柱没有刑冲者，可主长寿
        if self._piancai_gan_count > 0 and not self._conflict_present:
            self._add_clue(ShishenClue(Area.HEALTH, "可主长寿。", Shishen.PIANCAI, Condition.EXCESS, "偏财透干，四柱没有刑冲"))

        # 获取日、时地支索引（2和3）
        temp_idx_list = [2] if self._bazi_chart.without_time else [2, 3]
        for i in temp_idx_list:
            hidden_gans_shishen = self._updated_zhi_hidden_gans_shishen_list[i]
            # 检查是否专位偏财
            if self._is_zuozhuanwei_shishen(hidden_gans_shishen, Shishen.PIANCAI):
                # 检查时干是否是比肩或劫财
                hour_gan_shishen = self._updated_gan_shishen_list[3]
                if not self._conflict_present and hour_gan_shishen not in [Shishen.BIJIAN, Shishen.JIECAI]:
                    self._add_clue(ShishenClue(Area.FORTUNE, "晚年发达。", Shishen.PIANCAI, Condition.OTHER, "偏财坐专位于日、时地支，四柱不见刑冲，时干不是比肩、劫财"))

        # 偏财出天干，又与天、月德贵人同柱者
        for i, shishen in enumerate(self._updated_gan_shishen_list):
            if shishen == Shishen.PIANCAI:
                if any(shensha['chinese_name'] in ['天德贵人', '月德贵人'] for shensha in self._shensha_results if shensha['position'] == i):
                    if i in [0, 1]:
                        self._add_clue(ShishenClue(Area.FAMILY, "有贤德声名之父亲。", Shishen.PIANCAI, Condition.OTHER, "偏财在天干，又与天、月德贵人同柱在年、月"))
                    if i in [1, 3] and self._bazi_chart.gender == 'male':
                        self._add_clue(ShishenClue(Area.LOVE, "有贤慧之红颜知己。", Shishen.PIANCAI, Condition.OTHER, "男命偏财在天干，又与天、月德贵人同柱在月、时"))


        # 年干或月干有比肩或劫财，而时干偏财，同时地支有偏财
        if not self._bazi_chart.without_time:
            if (self._bazi_chart.year_gan_shishen in [Shishen.BIJIAN, Shishen.JIECAI] or self._bazi_chart.month_gan_shishen in [Shishen.BIJIAN, Shishen.JIECAI]) and self._updated_gan_shishen_list[3] == Shishen.PIANCAI:
                if any(Shishen.PIANCAI in self._updated_zhi_hidden_gans_shishen_list[i] for i in range(self.zhu_length)):
                    self._add_clue(ShishenClue(Area.CAREER, "年干或月干有比肩或劫财，而时干偏财，同时地支有偏财：主祖业凋零之后，再创事业。", Shishen.PIANCAI, Condition.EXCESS, "年干或月干有比肩或劫财，同时时柱比肩天透地藏"))
                    if self._conflict_present:
                        self._add_clue(ShishenClue(Area.CAREER, "年干或月干有比肩或劫财，而时干偏财，同时地支有偏财，如地支有刑冲，可以论为千金散尽还复来。", Shishen.PIANCAI, Condition.EXCESS, "年干或月干有比肩或劫财，同时时柱比肩天透地藏"))

        # 偏财与七杀同时透出天干，又同时存在于某个地支的藏干中
        if self._bazi_chart.gender == 'male':
            for i in range(self.zhu_length):
                if self._piancai_gan_count > 0 and self._qisha_gan_count > 0:
                    if any(Shishen.PIANCAI in self._updated_zhi_hidden_gans_shishen_list[i] and Shishen.QISHA in self._updated_zhi_hidden_gans_shishen_list[i] for i in range(self.zhu_length)):
                        if i == 0 or i == 1:
                            self._add_clue(ShishenClue(Area.FAMILY, "父子外和心不和。", Shishen.PIANCAI, Condition.OTHER, "男命偏财与七杀并位同根透出天干，透在年或月"))
                        if i == 1 or i == 3:
                            self._add_clue(ShishenClue(Area.LOVE, "有难伺候的女友。", Shishen.PIANCAI, Condition.OTHER, "男命偏财与七杀并位同根透出天干，透在月或时"))

        # 如果天干有偏财，地支藏干没有偏财
        if self._piancai_gan_count > 0 and self._piancai_zhi_count == 0:
            self._add_clue(ShishenClue(Area.FORTUNE, "财富俱皆明显于外表。实际财力不及外观之一半。财力被高估。", Shishen.PIANCAI, Condition.EXCESS, "偏财浮于天干"))
            self._add_clue(ShishenClue(Area.SOCIAL, "即使是真正已经没有现款，别人也肯相助。协助他人，时常超过自己能力之所负担。", Shishen.PIANCAI, Condition.EXCESS, "偏财浮于天干"))
            if self._bazi_chart.gender == 'male':
                self._add_clue(ShishenClue(Area.LOVE, "有粘人的女友。", Shishen.PIANCAI, Condition.EXCESS, "男命偏财浮于天干"))

    def _analyse_zhengcai(self):
        self._log_helper.debug("分析正财...")

        # 正财多者
        if self._is_over(Shishen.ZHENGCAI):
            self._add_clue(ShishenClue(Area.CHARACTER, "为人端正，有信用，行事稳重。", Shishen.ZHENGCAI, Condition.EXCESS, "正财多"))
            if ((self._zhengguan_gan_count > 0 and self._zhengguan_zhi_count) or (self._qisha_gan_count > 0) and (self._qisha_zhi_count > 0)) and self._bazi_chart.gender == 'male':
                self._add_clue(ShishenClue(Area.LOVE, "妻压夫。", Shishen.ZHENGCAI, Condition.EXCESS, "男命正财多，而且正官或者七杀天透地藏"))

        # 在年柱上，正财天透地藏
        if self._bazi_chart.year_gan_shishen == Shishen.ZHENGCAI and Shishen.ZHENGCAI in self._updated_zhi_hidden_gans_shishen_list[0]:
            self._add_clue(ShishenClue(Area.WEALTH, "家庭出生富裕。", Shishen.ZHENGCAI, Condition.YEAR_ZHU, "在年柱上，正财天透地藏"))
            self._add_clue(ShishenClue(Area.FAMILY, "不利母亲。", Shishen.ZHENGCAI, Condition.YEAR_ZHU, "在年柱上，正财天透地藏"))

        # 在月支地支第一个藏干为正财或偏财，不遇冲刑者
        if self._updated_zhi_hidden_gans_shishen_list[1][0] in [Shishen.ZHENGCAI, Shishen.PIANCAI]:
            if not self._is_chong_present( 1) and not self._is_sanxing_present(1) and not self._is_xiangxing_present(1):
                self._add_clue(ShishenClue(Area.CHARACTER, "生活端正朴实。", Shishen.ZHENGCAI, Condition.MONTH_ZHI, "正财得月令，不遇冲刑"))
                self._add_clue(ShishenClue(Area.CAREER, "多为理财之财经人士。", Shishen.ZHENGCAI, Condition.MONTH_ZHI, "正财得月令，不遇冲刑"))
                if self._bazi_chart.gender == 'male':
                    self._add_clue(ShishenClue(Area.LOVE, "必得有助力之妻室。但亦主母亲与妻子不和。", Shishen.ZHENGCAI, Condition.MONTH_ZHI, "男命正财得月令，不遇冲刑"))

        # 正财天干二见以上者
        if self._zhengcai_gan_count >= 2:
            self._add_clue(ShishenClue(Area.CAREER, "财源来于多途，大都是兼营好几种生意之人士，容易倾向人言亦言的拿不定主意，做生意有抢新潮的倾向。", Shishen.ZHENGCAI, Condition.EXCESS, "天干中有至少两个正财"))

        # 正财多见天干，地支没有正财和偏财
        if self._zhengcai_gan_count > 1:
            if self._zhengcai_zhi_count == 0 and self._piancai_gan_count == 0:
                self._add_clue(ShishenClue(Area.WEALTH, "虚富而不踏实。", Shishen.ZHENGCAI, Condition.EXCESS, "正财浮于天干"))
        # 天干有至少2个正财，地支有正财或偏财，日主身弱者
            elif self._power_results.rizhu_strength < 0 and self._bazi_chart.gender == 'male':
                self._add_clue(ShishenClue(Area.LOVE, "惧内，妻子有权。", Shishen.ZHENGCAI, Condition.EXCESS, "男命正财浮于天干"))

        # 正财与正官同时透出天干，又同时存在于某个地支的藏干中
        if self._zhengcai_gan_count > 0 and self._zhengguan_gan_count > 0:
            label = False
            for i, zhi in enumerate(self._bazi_chart.zhi_list):
                if Shishen.ZHENGCAI in self._updated_zhi_hidden_gans_shishen_list[i] and Shishen.ZHENGGUAN in self._updated_zhi_hidden_gans_shishen_list[i]:
                    label = True
            if label:
                self._add_clue(ShishenClue(Area.FAMILY, "书香门第之世家子弟。", Shishen.ZHENGCAI, Condition.OTHER, "正财与正官并位同根透出天干"))

        
        if not self._bazi_chart.without_time:
            # 特定日柱和时支配置
            if self._bazi_chart.day_gan == Gan.WU and self._bazi_chart.day_zhi == Zhi.ZI and self._bazi_chart.month_zhi != Zhi.WU and self._bazi_chart.hour_zhi != Zhi.WU:
                self._add_clue(ShishenClue(Area.LOVE, "得勤俭能持家的贤淑家室。", Shishen.ZHENGCAI, Condition.DAY_ZHI, "正财专位于日支，同时不受冲"))

        # 日或时地支坐专位正财，天干地支又同时有正官
        temp_idx_list = [2] if self._bazi_chart.without_time else [2, 3]
        for i in temp_idx_list:
            zhi = self._bazi_chart.get_zhi_by_index(i)
            if self._is_zuozhuanwei_shishen(self._updated_zhi_hidden_gans_shishen_list[i], Shishen.ZHENGCAI):
                if self._zhengguan_gan_count > 0 and self._zhengguan_zhi_count > 0:
                    self._add_clue(ShishenClue(Area.FORTUNE, "中年以后发，靠自己之努力，独立富贵。", Shishen.ZHENGCAI, Condition.OTHER, "正财专位于日或时支，同时正官天透地藏"))

        # 日柱壬午、癸巳，只要四柱没有刑冲，禄马同乡，大吉
        if (self._bazi_chart.day_gan == Gan.REN and self._bazi_chart.day_zhi == Zhi.WU) or (self._bazi_chart.day_gan == Gan.GUI and self._bazi_chart.day_zhi == Zhi.SI):
            if not self._conflict_present:
                self._add_clue(ShishenClue(Area.FORTUNE, "大吉。", Shishen.ZHENGCAI, Condition.DAY_ZHI, "日主自坐财官印，禄马同乡"))

        
        if not self._bazi_chart.without_time:
            # 时干正财，或者正财在时支坐专位
            if not self._bazi_chart.without_time:
                if self._updated_gan_shishen_list[3] == Shishen.ZHENGCAI or self._is_zuozhuanwei_shishen(self._updated_zhi_hidden_gans_shishen_list[3], Shishen.ZHENGCAI):
                    if not self._conflict_present:
                        self._add_clue(ShishenClue(Area.CHARACTER, "个性急，口快心直。不喜拖泥带水。", Shishen.ZHENGCAI, Condition.HOUR_ZHU, "正财在时干或专位于时支，同时无冲刑"))
                        if self._bazi_chart.gender == 'male':
                            self._add_clue(ShishenClue(Area.LOVE, "得美妻、佳子。", Shishen.ZHENGCAI, Condition.HOUR_ZHU, "男命正财在时干或专位于时支，同时无冲刑"))
                    else:
                        self._add_clue(ShishenClue(Area.CHARACTER, "有浮躁、不耐久之不良倾向。", Shishen.ZHENGCAI, Condition.HOUR_ZHU, "正财在时干或专位于时支，同时有冲刑"))

                # 时支专位正财者，男命经常作二子之论断
                if self._is_zuozhuanwei_shishen(self._updated_zhi_hidden_gans_shishen_list[3], Shishen.ZHENGCAI) and self._bazi_chart.gender == 'male':
                    self._add_clue(ShishenClue(Area.CHILDREN, "经常作二子之论断。", Shishen.ZHENGCAI, Condition.HOUR_ZHU, "男命时支专位正财"))

        # 四柱干支，皆无正财：（男命）主婚姻甚迟
        if self._zhengcai_gan_count == 0 and self._zhengcai_zhi_count == 0 and self._bazi_chart.gender == 'male':
            self._add_clue(ShishenClue(Area.LOVE, "婚姻甚迟。", Shishen.ZHENGCAI, Condition.LACK, "男命四柱干支，皆无正财"))

        # 财坐空亡，主财不能久持，纵然是富命，亦是属于虚象
        for i, zhi in enumerate(self._bazi_chart.zhi_list):
            if Shishen.ZHENGCAI in self._updated_zhi_hidden_gans_shishen_list[i] and self._is_shensha_present("Kongwang", i):
                self._add_clue(ShishenClue(Area.FORTUNE, "财不能久持，纵然是富命，亦是属于虚象。", Shishen.ZHENGCAI, Condition.SITTING_ON_EMPTY, "财坐空亡"))

        # 财坐绝、墓者，不利婚姻（男命）
        for i, zhi in enumerate(self._bazi_chart.zhi_list):
            zhengcai_gan = Gan.from_chinese(get_shishen_gan(self._bazi_chart.day_gan._gan.chinese_name, "正财"))
            if self._bazi_chart.gender == 'male' and (Shishen.ZHENGCAI in self._updated_zhi_hidden_gans_shishen_list[i] or self._updated_gan_shishen_list[i] == Shishen.ZHENGCAI) and (get_tiangandizhi_state(zhengcai_gan, "绝") == zhi or get_tiangandizhi_state(zhengcai_gan, "墓") == zhi):
                self._add_clue(ShishenClue(Area.LOVE, "不利婚姻。", Shishen.ZHENGCAI, Condition.SITTING_ON_JUE, "男命财坐绝、墓"))

        # 月支是日主的正财对应的干的禄（女命）
        zhengcai_gan = get_shishen_gan(self._bazi_chart.day_gan._gan.chinese_name, '正财')
        zhengcai_gan_lu = get_tiangandizhi_state(zhengcai_gan, "禄")
        if self._bazi_chart.gender == 'female' and self._bazi_chart.month_zhi == zhengcai_gan_lu:
            self._add_clue(ShishenClue(Area.LOVE, "婚姻方面，近似现实性之婚姻。", Shishen.ZHENGCAI, Condition.MONTH_ZHI, "女命月支是正财的禄"))

        # 正财若与驿马同一柱（女命）
        for i, zhi in enumerate(self._bazi_chart.zhi_list):
            if self._bazi_chart.gender == 'female' and (self._updated_gan_shishen_list[i] == Shishen.ZHENGCAI or Shishen.ZHENGCAI in self._updated_zhi_hidden_gans_shishen_list[i]) and self._is_shensha_present("Yima", i):
                self._add_clue(ShishenClue(Area.CHARACTER, "勤力持家。", Shishen.ZHENGCAI, Condition.OTHER, "女命正财与驿马同柱"))

        # 正财坐桃花（女命）不吉
        for i, zhi in enumerate(self._bazi_chart.zhi_list):
            if self._bazi_chart.gender == 'female' and (self._updated_gan_shishen_list[i] == Shishen.ZHENGCAI or Shishen.ZHENGCAI in self._updated_zhi_hidden_gans_shishen_list[i]) and self._is_shensha_present("Taohua", i):
                self._add_clue(ShishenClue(Area.LOVE, "感情不稳定。", Shishen.ZHENGCAI, Condition.OTHER, "女命正财坐桃花"))

        # 出生于甲戌日或乙亥日者（女命）主迟婚
        if self._bazi_chart.gender == 'female' and (self._bazi_chart.day_gan == Gan.JIA and self._bazi_chart.day_zhi == Zhi.XU or self._bazi_chart.day_gan == Gan.YI and self._bazi_chart.day_zhi == Zhi.HAI):
            self._add_clue(ShishenClue(Area.LOVE, "主迟婚。", Shishen.ZHENGCAI, Condition.DAY_ZHU, "女命出生于甲戌日或乙亥日"))

    def _analyse_zhengguan(self):
        self._log_helper.debug("分析正官...")

        # 1. 正官多者
        if self._is_over(Shishen.ZHENGGUAN):
            self._add_clue(ShishenClue(Area.CHARACTER, "为人性和、笃实。", Shishen.ZHENGGUAN, Condition.EXCESS, "正官多"))

        # 2. 正官在年柱，透出天干者
        if self._updated_gan_shishen_list[0] == Shishen.ZHENGGUAN:
            self._add_clue(ShishenClue(Area.FAMILY, "家庭出身于书香门第。", Shishen.ZHENGGUAN, Condition.YEAR_GAN, "正官在年柱，透出天干"))

        if not self._bazi_chart.without_time:
            # 3. 正官在时柱，坐专位地支者
            if self._is_zuozhuanwei_shishen(self._updated_zhi_hidden_gans_shishen_list[3], Shishen.ZHENGGUAN):
                self._add_clue(ShishenClue(Area.CHILDREN, "男命主看得力之子息。", Shishen.ZHENGGUAN, Condition.HOUR_ZHU, "正官在时柱，坐专位地支"))

            # 4. 男命见年干、时干为正官
            if self._bazi_chart.gender == 'male' and self._bazi_chart.year_gan_shishen == Shishen.ZHENGGUAN and self._bazi_chart.hour_gan_shishen == Shishen.ZHENGGUAN:
                self._add_clue(ShishenClue(Area.CHILDREN, "为正官二头挂，对子息头胎不利。", Shishen.ZHENGGUAN, Condition.HOUR_GAN, "男命见年干、时干为正官"))

        # 5. 天干正官，地支比肩或劫财
        for i in range(self.zhu_length):
            if self._updated_gan_shishen_list[i] == Shishen.ZHENGGUAN:
                if Shishen.BIJIAN == self._updated_zhi_hidden_gans_shishen_list[i][0] or Shishen.JIECAI == self._updated_zhi_hidden_gans_shishen_list[i][0]:
                    self._add_clue(ShishenClue(Area.SOCIAL, "亲友之间，不宜合作事业，不过善于经营东山再起之事业。", Shishen.ZHENGGUAN, Condition.OTHER, "同一柱中，天干正官，地支比肩或劫财"))

        # 6. 正官天透地藏，四柱不透财、印
        if self._zhengguan_gan_count > 0 and self._zhengguan_zhi_count > 0 and self._zhengcai_gan_count == 0 and self._piancai_gan_count == 0 and self._zhengyin_gan_count == 0:
            self._add_clue(ShishenClue(Area.CHARACTER, "笃厚之守份人士。", Shishen.ZHENGGUAN, Condition.EXCESS, "正官天透地藏，四柱不透财、印"))

        # 7. 正官与伤官同时透出天干，又同时存在于某个地支的藏干中
        if self._shangguan_gan_count > 0 and self._shangguan_zhi_count > 0:
            for i in range(self.zhu_length):
                if Shishen.ZHENGGUAN in self._updated_zhi_hidden_gans_shishen_list[i] and Shishen.SHANGGUAN in self._updated_zhi_hidden_gans_shishen_list[i]:
                    if set(self._geju_analysis_results).issubset({GejuEnum.ZHENGGUAN_GE, GejuEnum.SHANGGUAN_GE}):
                        self._add_clue(ShishenClue(Area.CAREER, "多失策。", Shishen.ZHENGGUAN, Condition.OTHER, "正官与伤官并位同根透出天干，格局只有正官格和伤官格"))
                    if self._bazi_chart.gender == 'female':
                        self._add_clue(ShishenClue(Area.LOVE, "眷属远离，婚姻不美满。", Shishen.ZHENGGUAN, Condition.OTHER, "女命正官与伤官并位同根透出天干"))

        # 8. 正官坐七杀
        for i in range(self.zhu_length):
            if Shishen.ZHENGGUAN == self._updated_gan_shishen_list[i] and Shishen.QISHA in self._updated_zhi_hidden_gans_shishen_list[i]:
                if self._bazi_chart.gender == 'male':
                    self._add_clue(ShishenClue(Area.CAREER, "多受责斥，恐有讼诉之灾。", Shishen.ZHENGGUAN, Condition.OTHER, "男命正官坐七杀"))
                else:
                    self._add_clue(ShishenClue(Area.LOVE, "大不利于婚姻。", Shishen.ZHENGGUAN, Condition.OTHER, "女命正官坐七杀"))

        # 9. 正官坐羊刃
        for i in range(self.zhu_length):
            if Shishen.ZHENGGUAN == self._updated_gan_shishen_list[i] and self._is_shensha_present("Yangren", i):
                self._add_clue(ShishenClue(Area.CAREER, "多为有力不从心之事。", Shishen.ZHENGGUAN, Condition.OTHER, "正官坐羊刃"))

        # 10. 正官坐正印，或同时透出天干，又同时存在于某个地支的藏干中
        if (any(Shishen.ZHENGGUAN == self._updated_gan_shishen_list[i] and Shishen.ZHENGYIN in self._updated_zhi_hidden_gans_shishen_list[i] for i in range(self.zhu_length))) or (any(Shishen.ZHENGGUAN in self._updated_zhi_hidden_gans_shishen_list[i] and Shishen.ZHENGYIN in self._updated_zhi_hidden_gans_shishen_list[i] for i in range(self.zhu_length)) and self._zhengguan_gan_count > 0 and self._zhengyin_gan_count > 0):
            if not self._conflict_present:
                self._add_clue(ShishenClue(Area.FORTUNE, "吉祥。", Shishen.ZHENGGUAN, Condition.OTHER, "正官坐正印，或正官与正印并位同根透出天干"))

        # 11. 正财或偏财、正官、正印同时在天干地支中存在，无刑冲合会
        if ((self._zhengcai_gan_count > 0 or self._piancai_gan_count > 0) and self._zhengguan_gan_count > 0 and self._zhengyin_gan_count > 0 and ((self._zhengcai_zhi_count > 0 or self._piancai_zhi_count > 0) and self._zhengguan_zhi_count > 0 and self._zhengyin_zhi_count > 0)):
            if not self._conflict_present and not any(self._is_sanhe_present(idx) or self._is_sanhui_present(idx) or self._is_liuhe_present(idx) for idx in range(self.zhu_length)):
                self._add_clue(ShishenClue(Area.FORTUNE, "最为有福。", Shishen.ZHENGGUAN, Condition.EXCESS, "正财或偏财、正官、正印同时在天干地支中存在，无刑冲合会"))

        # 女命特定分析规则
        if self._bazi_chart.gender == 'female':
            # 12. 年、月二天干是正官与七杀
            if (Shishen.ZHENGGUAN in [self._bazi_chart.year_gan_shishen, self._bazi_chart.month_gan_shishen] and Shishen.QISHA in [self._bazi_chart.year_gan_shishen, self._bazi_chart.month_gan_shishen]):
                self._add_clue(ShishenClue(Area.LOVE, "三十岁以前，婚姻不稳定。", Shishen.ZHENGGUAN, Condition.EXCESS, "女命年、月二天干是正官与七杀"))

            # 13. 月支是正官的墓、绝之位
            zhengguan_gan = Gan.from_chinese(get_shishen_gan(self._bazi_chart.day_gan._chinese_name, "正官"))
            if self._bazi_chart.month_zhi == get_tiangandizhi_state(zhengguan_gan, "墓") or self._bazi_chart.month_zhi == get_tiangandizhi_state(zhengguan_gan, "绝"):
                self._add_clue(ShishenClue(Area.LOVE, "迟婚或特殊的婚姻。", Shishen.ZHENGGUAN, Condition.SITTING_ON_JUE, "女命月支是正官的墓、绝之位"))

            # 14. 天干只有一个正官，同时和天德或月德贵人同柱，地支不见刑冲
            if self._zhengguan_gan_count == 1 and any((self._is_shensha_present("Tiandeguiren", i) or self._is_shensha_present("Yuede", i)) and self._updated_gan_shishen_list[i] == Shishen.ZHENGGUAN for i in range(self.zhu_length)):
                if not self._conflict_present:
                    self._add_clue(ShishenClue(Area.LOVE, "贤淑而有事业成就的丈夫。", Shishen.ZHENGGUAN, Condition.EXCESS, "女命天干只有一个正官，同时和天德或月德贵人同柱，地支不见刑冲"))

            # 15. 日坐正官专位者
            if self._is_zuozhuanwei_shishen(self._updated_zhi_hidden_gans_shishen_list[2], Shishen.ZHENGGUAN):
                self._add_clue(ShishenClue(Area.LOVE, "淑女。", Shishen.ZHENGGUAN, Condition.DAY_ZHU, "女命日坐正官专位"))

            # 16. 正官并驿马，在月柱
            if self._is_shensha_present("Yima", 1) and self._bazi_chart.month_gan_shishen == Shishen.ZHENGGUAN:
                self._add_clue(ShishenClue(Area.SOCIAL, "主颇有人缘，善交际之女命。", Shishen.ZHENGGUAN, Condition.MONTH_ZHI, "女命月柱正官并驿马"))

            # 17. 正官坐正官，有婚变之兆
            if any(self._is_zuozhuanwei_shishen(self._updated_zhi_hidden_gans_shishen_list[i], Shishen.ZHENGGUAN) and self._updated_gan_shishen_list[i] == Shishen.ZHENGGUAN for i in range(self.zhu_length)):
                self._add_clue(ShishenClue(Area.LOVE, "有婚变之兆。", Shishen.ZHENGGUAN, Condition.MONTH_ZHI, "女命某柱正官坐正官"))

            # 18. 正官在天干有至少两个合
            if any(self._is_wuhe_present(i) > 1 and self._updated_gan_shishen_list[i] == Shishen.ZHENGGUAN for i in range(self.zhu_length)):
                self._add_clue(ShishenClue(Area.LOVE, "媚而坎坷。", Shishen.ZHENGGUAN, Condition.EXCESS, "女命正官在天干有至少两个合"))

            # 19. 月支第一个藏干十神是正官，格局包含伤官格
            if self._updated_zhi_hidden_gans_shishen_list[1][0] == Shishen.ZHENGGUAN:
                if GejuEnum.SHANGGUAN_GE in self._geju_analysis_results:
                    self._add_clue(ShishenClue(Area.LOVE, "难作正妻。", Shishen.ZHENGGUAN, Condition.MONTH_ZHI, "月支正官当令，而在其他干支之中，却成伤官格"))

            # 20. 年、月正官天透地藏，而在日、时地支见专位七杀，再有驿马、桃花
            temp_idx_list = [2] if self._bazi_chart.without_time else [2, 3]
            if (self._bazi_chart.year_gan_shishen == Shishen.ZHENGGUAN or self._bazi_chart.month_gan_shishen == Shishen.ZHENGGUAN) and ( Shishen.ZHENGGUAN in self._updated_zhi_hidden_gans_shishen_list[0] and Shishen.ZHENGGUAN in self._updated_zhi_hidden_gans_shishen_list[1]) and any(self._is_zuozhuanwei_shishen(self._updated_zhi_hidden_gans_shishen_list[i], Shishen.QISHA) for i in temp_idx_list) and any(self._is_shensha_present("Yima", i) or self._is_shensha_present("Taohua", i) for i in range(self.zhu_length)):
                self._add_clue(ShishenClue(Area.LOVE, "婚姻有梅开二度之虞。", Shishen.ZHENGGUAN, Condition.EXCESS, "女命年、月正官天透地藏，而在日、时地支见专位七杀，再有驿马、桃花"))

            # 21. 正官坐桃花，主夫良
            if any(self._is_shensha_present("Taohua", i) and self._updated_zhi_hidden_gans_shishen_list[i][0] == Shishen.ZHENGGUAN for i in range(self.zhu_length)):
                self._add_clue(ShishenClue(Area.LOVE, "夫良。", Shishen.ZHENGGUAN, Condition.EXCESS, "女命正官坐桃花"))
                
    def _analyse_qisha(self):
        self._log_helper.debug("分析七杀...")

        # 1. 七杀过多
        if self._is_over(Shishen.QISHA):
            self._add_clue(ShishenClue(Area.CHARACTER, "扶弱挫强，见义勇为，固执不易听人劝言。", Shishen.QISHA, Condition.EXCESS, "七杀过多"))

        # 2. 七杀在年干
        if self._bazi_chart.year_gan_shishen == Shishen.QISHA:
            self._add_clue(ShishenClue(Area.FAMILY, "出生于清贫世家，或者幼年多疾。", Shishen.QISHA, Condition.YEAR_GAN, "七杀在年干"))

        # 4. 天元坐杀，若无羊刃，地支也无食神藏干
        if self._updated_zhi_hidden_gans_shishen_list[2][0] == Shishen.QISHA:
            if not any(self._is_shensha_present("Yangren", i) or Shishen.SHISHEN == self._updated_zhi_hidden_gans_shishen_list[i][0] for i in range(self.zhu_length)):
                self._add_clue(ShishenClue(Area.CHARACTER, "性急伶俐，心巧聪明。对人常有不信任之心，猜疑心重。", Shishen.QISHA, Condition.DAY_ZHI, "天元坐杀，无羊刃，地支也无食神藏干"))

        # 5. 天元坐杀于专位者，乙酉日、己卯日，忌日支七杀透月干
        if (self._bazi_chart.day_gan == Gan.YI and self._bazi_chart.day_zhi == Zhi.YOU) or (self._bazi_chart.day_gan == Gan.JI and self._bazi_chart.day_zhi == Zhi.MAO):
            if self._bazi_chart.month_gan_shishen == Shishen.QISHA:
                if not any(self._is_shensha_present("Yangren", i) or Shishen.SHISHEN == self._updated_zhi_hidden_gans_shishen_list[i][0] for i in range(self.zhu_length)):
                    self._add_clue(ShishenClue(Area.HEALTH, "体弱多病。", Shishen.QISHA, Condition.MONTH_GAN, "天元坐杀于专位者，日支七杀透月干"))

        # 6. 七杀在年或月天干，地支无七杀
        if (self._bazi_chart.year_gan_shishen == Shishen.QISHA or self._bazi_chart.month_gan_shishen == Shishen.QISHA) and self._qisha_zhi_count == 0:
            self._add_clue(ShishenClue(Area.CHARACTER, "性好变易，不易有定性。", Shishen.QISHA, Condition.YEAR_GAN, "七杀浮于年月"))

        if not self._bazi_chart.without_time:
            # 7. 七杀坐桃花，丁亥日、丁卯日、丁未日，生于子时，时支又逢刑冲
            if (self._bazi_chart.day_gan == Gan.DING and self._bazi_chart.day_zhi in {Zhi.HAI, Zhi.MAO, Zhi.WEI}) and self._bazi_chart.hour_zhi == Zhi.ZI:
                if self._is_chong_present( 3) or self._is_sanxing_present(3) or self._is_xiangxing_present(3):
                    self._add_clue(ShishenClue(Area.LOVE, "因感情而引祸。", Shishen.QISHA, Condition.HOUR_ZHI, "七杀坐桃花，时支又逢刑冲"))
                    self._add_clue(ShishenClue(Area.YUN, "午运尤不利。", Shishen.QISHA, Condition.HOUR_ZHI, "七杀坐桃花，时支又逢刑冲"))

        # 8. 七杀坐七杀在年月
        if any(self._updated_gan_shishen_list[i] == Shishen.QISHA and self._updated_zhi_hidden_gans_shishen_list[i] == Shishen.QISHA for i in range(2)):
            self._add_clue(ShishenClue(Area.FAMILY, "六亲福薄。", Shishen.QISHA, Condition.YEAR_ZHI, "七杀坐七杀在年月"))

        # 9. 七杀坐正印或杀印相生
        if any(self._updated_gan_shishen_list[i] == Shishen.QISHA and self._updated_zhi_hidden_gans_shishen_list[i] == Shishen.ZHENGYIN for i in range(self.zhu_length)) or (self._zhengyin_gan_count > 0 and self._qisha_gan_count > 0):
            self._add_clue(ShishenClue(Area.CAREER, "精明练达的商人。", Shishen.QISHA, Condition.EXCESS, "杀印相生"))

        if not self._bazi_chart.without_time:
            # 10. 七杀在时干且月支藏干有七杀
            if self._updated_gan_shishen_list[3] == Shishen.QISHA and Shishen.QISHA in self._updated_zhi_hidden_gans_shishen_list[1]:
                self._add_clue(ShishenClue(Area.CHARACTER, "性直不屈，有不计困难，坚持己见的性格。", Shishen.QISHA, Condition.HOUR_GAN, "七杀在时干通根于月支"))

            # 11. 七杀在年干、时干，称之为七杀二头挂
            if self._bazi_chart.year_gan_shishen == Shishen.QISHA and self._bazi_chart.hour_gan_shishen == Shishen.QISHA:
                if self._bazi_chart.gender == 'male':
                    self._add_clue(ShishenClue(Area.CHILDREN, "七杀二头挂，头胎子息有麻烦。", Shishen.QISHA, Condition.YEAR_GAN, "男命七杀在年干、时干"))
                else:
                    self._add_clue(ShishenClue(Area.LOVE, "七杀二头挂，婚姻有阻碍。", Shishen.QISHA, Condition.YEAR_GAN, "女命七杀在年干、时干"))

            # 12. 月时二天干是七杀者，主体弱多病
            if self._updated_gan_shishen_list[1] == Shishen.QISHA and self._updated_gan_shishen_list[3]== Shishen.QISHA:
                self._add_clue(ShishenClue(Area.HEALTH, "主体弱多病。", Shishen.QISHA, Condition.HOUR_GAN, "月时二天干七杀"))

        # 13. 地支第一位藏干七杀，坐入三刑或对冲
        for i in range(self.zhu_length):
            if self._updated_zhi_hidden_gans_shishen_list[i] == Shishen.QISHA and self._is_sanxing_present(i) or self._is_chong_present( i) and self._bazi_chart.gender == 'female':
                self._add_clue(ShishenClue(Area.LOVE, "夫妻不和。", Shishen.QISHA, Condition.OTHER, "女命地支七杀，坐入三刑或对冲"))

        # 14. 七杀坐空亡
        for i in range(self.zhu_length):
            if self._updated_gan_shishen_list[i] == Shishen.QISHA and self._is_shensha_present("Kongwang", i) and self._bazi_chart.gender == 'female':
                self._add_clue(ShishenClue(Area.LOVE, "夫缘薄。", Shishen.QISHA, Condition.OTHER, "女命七杀坐空亡"))
                
    def _analyse_shishen(self):
        self._log_helper.debug("分析食神...")

        # 食神多者
        if self._is_over(Shishen.SHISHEN):
            if self._bijian_gan_count + self._jiecai_gan_count > 0:
                self._add_clue(ShishenClue(Area.CHARACTER, "性宽厚，带比肩、劫财者，好施舍，乐于作社会服务事项。", Shishen.SHISHEN, Condition.EXCESS, "食神多"))
        
            # 食神伤官不喜同时见天干
            if self._shangguan_gan_count > 0:
                self._add_clue(ShishenClue(Area.CAREER, "做事立志定向，往往太高，不容易对平常生活的标准满足。", Shishen.SHISHEN, Condition.EXCESS, "食伤混杂"))
        
            # 日支坐食神专位者
            if (self._bazi_chart.day_gan == Gan.GUI and self._bazi_chart.day_zhi == Zhi.MAO) or (self._bazi_chart.day_gan == Gan.JI and self._bazi_chart.day_zhi == Zhi.YOU):
                self._add_clue(ShishenClue(Area.HEALTH, "容易发胖", Shishen.SHISHEN, Condition.DAY_ZHI, "日支坐食神专位"))
                self._add_clue(ShishenClue(Area.FORTUNE, "有福。", Shishen.SHISHEN, Condition.DAY_ZHI, "日支坐食神专位"))
                if self._bazi_chart.gender == 'male':
                    self._add_clue(ShishenClue(Area.LOVE, "可得有助之妻。", Shishen.SHISHEN, Condition.DAY_ZHI, "男命日支坐食神专位"))
            
            if self._zhengcai_gan_count + self._zhengcai_zhi_count == 0 and self._piancai_gan_count + self._piancai_zhi_count == 0:
                # 食神多者无财难发越
                if self._shishen_gan_count + self._shishen_zhi_count > 3:
                    self._add_clue(ShishenClue(Area.WEALTH, "难暴富。", Shishen.SHISHEN, Condition.EXCESS, "食神多者无财难发越"))
            elif self._zhengcai_gan_count + self._piancai_gan_count > 0:
                self._add_clue(ShishenClue(Area.CHARACTER, "气量宽宏。", Shishen.SHISHEN, Condition.EXCESS, "食神多，有财透干"))
            
            # 七杀透干地支无七杀
            if self._qisha_gan_count > 0 and self._qisha_zhi_count == 0:
                self._add_clue(ShishenClue(Area.SOCIAL, "施予后后悔。", Shishen.SHISHEN, Condition.EXCESS, "食神多，七杀浮于天干"))
        
            # 女命食神成格
            if self._bazi_chart.gender == 'female' and GejuEnum.SHISHEN_GE in self._geju_analysis_results:
                if self._bazi_chart.day_gan.yinyang == Yinyang.YANG:
                    self._add_clue(ShishenClue(Area.CAREER, "适宜于社会性职业。", Shishen.SHISHEN, Condition.EXCESS, "女命阳日主食神成格"))
                else:
                    self._add_clue(ShishenClue(Area.CAREER, "适宜于上班族职业。", Shishen.SHISHEN, Condition.EXCESS, "女命阴日主食神成格"))
        
        # 一柱之中天干与地支第一位藏干是食神与七杀
        for i, shishen in enumerate(self._updated_gan_shishen_list):
            if shishen == Shishen.SHISHEN and self._updated_zhi_hidden_gans_shishen_list[i][0] == Shishen.QISHA or shishen == Shishen.QISHA and self._updated_zhi_hidden_gans_shishen_list[i][0] == Shishen.SHISHEN:
                self._add_clue(ShishenClue(Area.CHARACTER, "性格易怒，心中有不耐烦之压力。", Shishen.SHISHEN, Condition.OTHER, "食神与七杀同柱"))
        
        # 食神天干坐羊刃
        for i, shishen in enumerate(self._updated_gan_shishen_list):
            if shishen == Shishen.SHISHEN and self._is_shensha_present("Yangren", i):
                self._add_clue(ShishenClue(Area.CAREER, "劳禄之命。", Shishen.SHISHEN, Condition.OTHER, "天干食神坐羊刃"))
        
        # 一柱之中天干与地支第一位藏干是食神与偏印
        for i, shishen in enumerate(self._updated_gan_shishen_list):
            if shishen == Shishen.SHISHEN and self._updated_zhi_hidden_gans_shishen_list[i][0] == Shishen.PIANYIN or shishen == Shishen.PIANYIN and self._updated_zhi_hidden_gans_shishen_list[i][0] == Shishen.SHISHEN:
                if self._bazi_chart.gender == 'female':
                    self._add_clue(ShishenClue(Area.CHARACTER, "不利子女。", Shishen.SHISHEN, Condition.OTHER, "女命食神与偏印并位同根透干"))
        
        # 食神不宜与七杀、偏印齐成格 食神不宜与劫财、偏印齐出干
        if (
            GejuEnum.SHISHEN_GE in self._geju_analysis_results
            and GejuEnum.QISHA_GE in self._geju_analysis_results
            and GejuEnum.PIANYIN_GE in self._geju_analysis_results
        ) or (self._shishen_gan_count > 0 and self._jiecai_gan_count > 0 and self._pianyin_gan_count > 0):
            self._add_clue(ShishenClue(Area.HEALTH, "易体弱多病。", Shishen.SHISHEN, Condition.EXCESS, "食神与七杀、偏印齐成格或齐出干"))

    def _analyse_shangguan(self):
        self._log_helper.debug("分析伤官...")

        # 1. 伤官多者
        if self._is_over(Shishen.SHANGGUAN):
            self._add_clue(ShishenClue(Area.CHARACTER, "容易自视甚高。", Shishen.SHANGGUAN, Condition.EXCESS, "伤官过多"))
            self._add_clue(ShishenClue(Area.TALENT, "有才学、能力。", Shishen.SHANGGUAN, Condition.EXCESS, "伤官多"))
            if self._bazi_chart.gender == 'female':
                self._add_clue(ShishenClue(Area.LOVE, "感情缘淡，亦多有苦情。", Shishen.SHANGGUAN, Condition.EXCESS, "女命伤官过多"))

            # 3. 伤官天透地藏，正印透天干，无财
            if self._zhengyin_gan_count > 0 and self._zhengcai_gan_count + self._pianyin_gan_count == 0:
                self._add_clue(ShishenClue(Area.TALENT, "技艺、专长之人，却不是善于理财，亦带些有性格的倾向。", Shishen.SHANGGUAN, Condition.EXCESS, "伤官格，正印透天干，无财"))

        # 2. 伤官在天干，同柱有羊刃
        for i, shishen in enumerate(self._updated_gan_shishen_list):
            if shishen == Shishen.SHANGGUAN and self._is_shensha_present("Yangren", i):
                self._add_clue(ShishenClue(Area.CAREER, "背禄逐马，有力不从心之感。适合成为纯粹之精明商人。", Shishen.SHANGGUAN, Condition.SITTING_ON_YANGREN, "天干伤官坐羊刃"))

        # 4. 年、月天干都是伤官浮于天干
        if self._bazi_chart.year_gan_shishen == Shishen.SHANGGUAN and self._bazi_chart.month_gan_shishen == Shishen.SHANGGUAN and self._shangguan_zhi_count == 0:
            self._add_clue(ShishenClue(Area.FAMILY, "亲属很少，不适合居住大家庭生活的倾向。", Shishen.SHANGGUAN, Condition.YEAR_GAN, "伤官于年月浮于天干"))

        # 5. 月柱天干伤官，地支专位成伤官，女命夫缘不定
        if self._bazi_chart.month_gan_shishen == Shishen.SHANGGUAN and self._is_zuozhuanwei_shishen(self._updated_zhi_hidden_gans_shishen_list[1], Shishen.SHANGGUAN):
            if self._bazi_chart.gender == 'female':
                self._add_clue(ShishenClue(Area.LOVE, "月柱天干伤官，地支专位成伤官，夫缘不定。", Shishen.SHANGGUAN, Condition.MONTH_ZHU, "女命月干伤官、月支专位伤官"))

        # 6. 日主自坐专位伤官，庚子日，怕见刑冲，不利配偶
        if self._bazi_chart.day_gan == Gan.GENG and self._bazi_chart.day_zhi == Zhi.ZI:
            if self._is_chong_present(2) or self._is_sanxing_present(2) or self._is_xiangxing_present(2):
                self._add_clue(ShishenClue(Area.LOVE, "不利配偶。", Shishen.SHANGGUAN, Condition.DAY_ZHU, "日主自坐专位伤官见刑冲"))





