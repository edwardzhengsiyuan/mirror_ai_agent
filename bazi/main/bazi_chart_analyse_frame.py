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

# main/bazi_chart_analyse_frame.py 

import json
import copy
from datetime import datetime
from typing import Dict, Tuple, Any

from ..analysis.ditiansui_qiongtong_analysis import ditiansui_qiongtong_analysis
from ..analysis.geju.geju_analyser import GejuAnalyser
from ..analysis.hehua.hehua_analysis import HehuaAnalysis
from ..analysis.power.power_analysis import PowerAnalysis
from ..analysis.shensha.shensha_analyser import ShenShaAnalyser
from ..analysis.shishen.shishen_analyser import ShishenAnalyser
from ..analysis.xinghai.xinghai_analyser import XinghaiAnalyser
from ..analysis.compatibility.zodiac_compatibility_analyser import ZodiacCompatibilityAnalyser
from ..analysis.compatibility.wuxing_vector_compatibility_analyser import WuxingVectorCompatibilityAnalyser
from ..analysis.scoring.daily_fortune_analyser import DailyFortuneAnalyser
from ..core.bazi_chart import BaziChart, BaziChartGan, BaziChartZhi
from ..core.property import (
    Gan,
    Zhi,
    ShenshaEnum,
    Shishen,
    Wuxing,
    ns,
    strip_ns,
    NS_YINYANG,
    NS_WUXING,
    NS_GAN,
    NS_ZHI,
    NS_SHISHEN,
    NS_SHENGXIAO,
    NS_SHENSHA,
    NS_NAYIN,
    NS_DISHI,
    NS_SHENQIANGRUO,
    NS_GEJU,
    NS_GAN_RELATION_TYPE,
    NS_ZHI_RELATION_TYPE,
    NS_ZODIAC_COMPAT_RELATION,
    NS_ZODIAC_COMPAT_FAVORABILITY,
    NS_ZODIAC_COMPAT_DETAIL,
)
from ..utils.log_helper import LogHelper


class BaziChartAnalyseFrame:
    def __init__(
        self,
        lunar,
        gender,
        without_time: bool = False,
        enable_terminal_output: bool = True,
        compute_dayun: bool = True,
        only_compatibility: bool = False,
    ):
        self.res = dict()
        self.bazi_chart = BaziChart(lunar, gender, without_time, compute_dayun=compute_dayun)
        self.without_time = without_time
        self.analysis_results = {}
        self.log_helper = LogHelper(enable_terminal_output=enable_terminal_output)
        self.gender = gender
        self.liupan = ""
        self.guji = ""
        self.shensha_instances = []
        self.liunian_shensha = []

        # 性能优化：仅做合盘时跳过整盘分析与大运流年等结果构建
        # - get_compatibility_analysis() 只依赖 bazi_chart 与 log_helper，不依赖 analysis_results / res
        if not only_compatibility:
            # 记录八字原命盘
            self.log_bazi_chart()

            self.run_analysis()
            self.generate_basic_res()

    def generate_basic_res(self):
        def shensha_to_chinese(value: str) -> str:
            """
            将神煞枚举码（如 'SHENSHA:TIANYI' 或 'TIANYI'）转换为中文名（如 '天乙贵人'）。
            若无法映射则回退为去命名空间后的 code。
            """
            code = strip_ns(value) or value
            if not hasattr(self, "_shensha_cn_cache") or self._shensha_cn_cache is None:
                cache = {}
                # 只有完整原盘分析 run_analysis() 后才会有实例可映射中文名
                for inst in (self.shensha_instances or []):
                    try:
                        enum_code = ShenshaEnum[inst.__class__.__name__.upper()].value
                        cache[enum_code] = inst.chinese_name
                    except Exception:
                        continue
                self._shensha_cn_cache = cache
            return self._shensha_cn_cache.get(code, code)

        zhu_list = self.bazi_chart._zhu_list
        tai_ming_shen_zhu_list = self.bazi_chart._tai_ming_shen_zhu_list
        if self.without_time:
            name_list = ["year", "month", "day", "taiyuan", "minggong", "shengong"]
            len_zhu_list = 3
        else:
            name_list = ["year", "month", "day", "hour", "taiyuan", "minggong", "shengong"]
            len_zhu_list = 4
        zhu_name_list = [x + "_zhu" for x in name_list]
        gan_name_list = [x + "_gan" for x in name_list]
        zhi_name_list = [x + "_zhi" for x in name_list]
        self.res["zhu_list"] = dict()
        for i in range(len_zhu_list):
            zhu = zhu_list[i]
            gan = zhu.gan
            zhi = zhu.zhi
            self.res["zhu_list"][zhu_name_list[i]] = dict()
            self.res["zhu_list"][zhu_name_list[i]]["gan"] = dict()
            self.res["zhu_list"][zhu_name_list[i]]["zhi"] = dict()
            self.add_gan_info(gan, self.res["zhu_list"][zhu_name_list[i]]["gan"])
            self.add_zhi_info(zhi, self.res["zhu_list"][zhu_name_list[i]]["zhi"])
        for i in range(3):
            zhu = tai_ming_shen_zhu_list[i]
            gan = zhu.gan
            zhi = zhu.zhi
            self.res["zhu_list"][zhu_name_list[i + len_zhu_list]] = dict()
            self.res["zhu_list"][zhu_name_list[i + len_zhu_list]]["gan"] = dict()
            self.res["zhu_list"][zhu_name_list[i + len_zhu_list]]["zhi"] = dict()
            self.add_gan_info(gan, self.res["zhu_list"][zhu_name_list[i + len_zhu_list]]["gan"])
            self.add_zhi_info(zhi, self.res["zhu_list"][zhu_name_list[i + len_zhu_list]]["zhi"])
        self.res["nayin"] = [x.name for x in self.bazi_chart.nayin_list]
        self.res["daygan_dishi"] = [x.name for x in self.bazi_chart.dishi_list]
        self.res["zizuo_dishi"] = [x.name for x in self.bazi_chart.dishi_zizuo_list]
        self.res["xunkong"] = [[a.name, b.name] for (a, b) in self.bazi_chart.xunkong_list]
        self.res["startyun"] = self.bazi_chart.start_yun
        self.res["shensha"] = []
        for pos in self.analysis_results["shensha_sorted"]:
            shensha_name_list = [
                ShenshaEnum[x["name"].upper()].value
                for x in self.analysis_results["shensha_sorted"][pos]
            ]
            self.res["shensha"].append({"values": shensha_name_list})
        # 深拷贝一份，避免后续添加神煞/命名空间化时污染 BaziChart 内部数据
        self.res["yun"] = copy.deepcopy(self.bazi_chart.dayun_liunian_liuyue_frontend_res)
        yun_idx = 0
        self.log_helper.info(f"【大运简排】：")
        for yun in self.res["yun"]:
            if yun_idx > 0:
                gan = Gan[yun["gan"]]
                zhi = Zhi[yun["zhi"]]
                yun["shensha"] = self.search_shensha_enum_in_zhu(gan, zhi, self.bazi_chart)
                word = (
                    f'第{yun_idx}步运'
                    f'{Gan[yun["gan"]].chinese_name}{Zhi[yun["zhi"]].chinese_name}'
                    f'【{Shishen[yun["gan_shishen"]].chinese_name}{Shishen[yun["zhi_shishen"]].chinese_name}】'
                )
                self.log_helper.info(
                    f'{Gan[yun["gan"]].chinese_name}{Zhi[yun["zhi"]].chinese_name}{yun["year"]}'
                )
                if len(yun["shensha"]) > 0 or (len(yun.get("gan_relation", [])) + len(yun.get("zhi_relation", [])) > 0):
                    word += '('
                    if len(yun["shensha"]) > 0:
                        cn = ",".join([shensha_to_chinese(x) for x in yun["shensha"]])
                        word += f'神煞【{cn}】'
                    if len(yun.get("gan_relation", [])) + len(yun.get("zhi_relation", [])) > 0:
                        # 关系已改为结构化枚举对象，这里日志仅展示数量，避免影响输出
                        word += f'关系【{len(yun.get("gan_relation", [])) + len(yun.get("zhi_relation", []))}项】'
                    word += ')'
                word += '：'
                self.liunian_shensha.append(word)
            else:
                self.liunian_shensha.append("起运前")
            yun_idx += 1
            for nian in yun["liunian"]:
                gan = Gan[nian["gan"]]
                zhi = Zhi[nian["zhi"]]
                nian["shensha"] = self.search_shensha_enum_in_zhu(gan, zhi, self.bazi_chart)
                word = (
                    f'{nian["year"]}'
                    f'{Gan[nian["gan"]].chinese_name}{Zhi[nian["zhi"]].chinese_name}'
                    f'【{Shishen[nian["gan_shishen"]].chinese_name}{Shishen[nian["zhi_shishen"]].chinese_name}】'
                    f'{nian["age"]}岁'
                )
                if len(nian["shensha"]) > 0 or (len(nian.get("gan_relation", [])) + len(nian.get("zhi_relation", [])) > 0):
                    word += '('
                    if len(nian["shensha"]) > 0:
                        cn = ",".join([shensha_to_chinese(x) for x in nian["shensha"]])
                        word += f'神煞【{cn}】'
                    if len(nian.get("gan_relation", [])) + len(nian.get("zhi_relation", [])) > 0:
                        word += f'关系【{len(nian.get("gan_relation", [])) + len(nian.get("zhi_relation", []))}项】'
                    word += ')'
                word += '；'
                self.liunian_shensha.append(word)

        self.res["wuxing_proportions"] = dict()
        for wuxing, proportion in self.analysis_results["power_analysis"].wuxing_proportions.items():
            self.res["wuxing_proportions"][wuxing.name] = proportion
        self.res["shishen_proportions"] = dict()
        for shishen, proportion in self.analysis_results["power_analysis"].shishen_proportions.items():
            self.res["shishen_proportions"][shishen.name] = proportion
        self.res["shenqiangshenruo"] = self.analysis_results["power_analysis"].shenqiangruo.name
        self.res["rizhu"] = self.res["zhu_list"][zhu_name_list[2]]["gan"]
        self.res["shengxiao"] = self.bazi_chart.year_zhi.get().shengxiao.name
        self.res["geju"] = [g.name for g in self.analysis_results["geju_analysis"]]

        # 对外 JSON：把所有可枚举语义字段统一输出为带命名空间的枚举码（如 "GAN:WU"）
        self._namespace_basic_res(self.res)

        self.res_json = json.dumps(self.res)
        # with open("output.txt", "w", encoding="utf-8") as file:
        #     file.write(self.res_json)
        # print(self.find_yun_liu_nian_liuyue(1998))

        # 大运流年
        dayun_liunian_info = self.liunian_shensha
        dayun_liunian_info_str = "\n".join(dayun_liunian_info)
        self.liupan = f"【流年大运排盘】：\n{dayun_liunian_info_str}"

    def generate_basic_res_without_yun(self):
        """
        返回generate_basic_res中除去流年大运相关内容的结果，用于生时矫正。
        """
        self.generate_basic_res()  # 先生成完整结果
        res_copy = dict(self.res)
        # 移除流年大运相关内容
        if "yun" in res_copy:
            del res_copy["yun"]
        # 其他与流年大运相关的内容如self.liupan不返回
        return res_copy

    def _namespace_basic_res(self, res: dict) -> None:
        """把 basic_res 中所有可枚举语义字段统一转为 `NAMESPACE:CODE` 形式（原地修改）。"""

        def _ns_in_place(target: dict, key: str, namespace: str) -> None:
            if key in target:
                target[key] = ns(namespace, target[key])

        def _ns_list_in_place(values, namespace: str):
            if not isinstance(values, list):
                return values
            return [ns(namespace, v) for v in values]

        # zhu_list
        zhu_list = res.get("zhu_list", {})
        if isinstance(zhu_list, dict):
            for _zhu_name, zhu in zhu_list.items():
                if not isinstance(zhu, dict):
                    continue
                gan = zhu.get("gan")
                if isinstance(gan, dict):
                    _ns_in_place(gan, "name", NS_GAN)
                    _ns_in_place(gan, "wuxing", NS_WUXING)
                    _ns_in_place(gan, "yinyang", NS_YINYANG)
                    _ns_in_place(gan, "shishen", NS_SHISHEN)
                zhi = zhu.get("zhi")
                if isinstance(zhi, dict):
                    _ns_in_place(zhi, "name", NS_ZHI)
                    _ns_in_place(zhi, "wuxing", NS_WUXING)
                    _ns_in_place(zhi, "yinyang", NS_YINYANG)
                    hidden = zhi.get("hidden_gans")
                    if isinstance(hidden, list):
                        for hg in hidden:
                            if not isinstance(hg, dict):
                                continue
                            _ns_in_place(hg, "name", NS_GAN)
                            _ns_in_place(hg, "wuxing", NS_WUXING)
                            _ns_in_place(hg, "yinyang", NS_YINYANG)
                            _ns_in_place(hg, "shishen", NS_SHISHEN)

        # top-level simple lists
        if isinstance(res.get("nayin"), list):
            res["nayin"] = _ns_list_in_place(res["nayin"], NS_NAYIN)
        if isinstance(res.get("daygan_dishi"), list):
            res["daygan_dishi"] = _ns_list_in_place(res["daygan_dishi"], NS_DISHI)
        if isinstance(res.get("zizuo_dishi"), list):
            res["zizuo_dishi"] = _ns_list_in_place(res["zizuo_dishi"], NS_DISHI)
        if isinstance(res.get("xunkong"), list):
            xk = []
            for pair in res["xunkong"]:
                if isinstance(pair, list):
                    xk.append([ns(NS_ZHI, v) for v in pair])
                else:
                    xk.append(pair)
            res["xunkong"] = xk

        # shensha (top-level)
        if isinstance(res.get("shensha"), list):
            for item in res["shensha"]:
                if isinstance(item, dict) and isinstance(item.get("values"), list):
                    item["values"] = _ns_list_in_place(item["values"], NS_SHENSHA)

        def _namespace_relations(rel_list, rel_type_ns: str, member_ns: str):
            if not isinstance(rel_list, list):
                return rel_list
            for r in rel_list:
                if not isinstance(r, dict):
                    continue
                if "type" in r:
                    r["type"] = ns(rel_type_ns, r["type"])
                if isinstance(r.get("members"), list):
                    r["members"] = [ns(member_ns, m) for m in r["members"]]
            return rel_list

        def _namespace_yun_list(yun_list):
            if not isinstance(yun_list, list):
                return
            for yun in yun_list:
                if not isinstance(yun, dict):
                    continue
                # gan/zhi and derived fields
                _ns_in_place(yun, "gan", NS_GAN)
                _ns_in_place(yun, "zhi", NS_ZHI)
                _ns_in_place(yun, "gan_wuxing", NS_WUXING)
                _ns_in_place(yun, "zhi_wuxing", NS_WUXING)
                _ns_in_place(yun, "gan_shishen", NS_SHISHEN)
                _ns_in_place(yun, "zhi_shishen", NS_SHISHEN)
                if isinstance(yun.get("shensha"), list):
                    yun["shensha"] = _ns_list_in_place(yun["shensha"], NS_SHENSHA)
                _namespace_relations(yun.get("gan_relation"), NS_GAN_RELATION_TYPE, NS_GAN)
                _namespace_relations(yun.get("zhi_relation"), NS_ZHI_RELATION_TYPE, NS_ZHI)

                liunian = yun.get("liunian")
                if isinstance(liunian, list):
                    for nian in liunian:
                        if not isinstance(nian, dict):
                            continue
                        _ns_in_place(nian, "gan", NS_GAN)
                        _ns_in_place(nian, "zhi", NS_ZHI)
                        _ns_in_place(nian, "gan_wuxing", NS_WUXING)
                        _ns_in_place(nian, "zhi_wuxing", NS_WUXING)
                        _ns_in_place(nian, "gan_shishen", NS_SHISHEN)
                        _ns_in_place(nian, "zhi_shishen", NS_SHISHEN)
                        if isinstance(nian.get("shensha"), list):
                            nian["shensha"] = _ns_list_in_place(nian["shensha"], NS_SHENSHA)
                        _namespace_relations(nian.get("gan_relation"), NS_GAN_RELATION_TYPE, NS_GAN)
                        _namespace_relations(nian.get("zhi_relation"), NS_ZHI_RELATION_TYPE, NS_ZHI)

                        liuyue = nian.get("liuyue")
                        if isinstance(liuyue, list):
                            for yue in liuyue:
                                if not isinstance(yue, dict):
                                    continue
                                _ns_in_place(yue, "gan", NS_GAN)
                                _ns_in_place(yue, "zhi", NS_ZHI)
                                _ns_in_place(yue, "gan_wuxing", NS_WUXING)
                                _ns_in_place(yue, "zhi_wuxing", NS_WUXING)
                                _ns_in_place(yue, "gan_shishen", NS_SHISHEN)
                                _ns_in_place(yue, "zhi_shishen", NS_SHISHEN)
                                _namespace_relations(yue.get("gan_relation"), NS_GAN_RELATION_TYPE, NS_GAN)
                                _namespace_relations(yue.get("zhi_relation"), NS_ZHI_RELATION_TYPE, NS_ZHI)

        _namespace_yun_list(res.get("yun"))

        # proportions: keys are enums too
        if isinstance(res.get("wuxing_proportions"), dict):
            res["wuxing_proportions"] = {ns(NS_WUXING, k): v for k, v in res["wuxing_proportions"].items()}
        if isinstance(res.get("shishen_proportions"), dict):
            res["shishen_proportions"] = {ns(NS_SHISHEN, k): v for k, v in res["shishen_proportions"].items()}

        # other single enum fields
        _ns_in_place(res, "shenqiangshenruo", NS_SHENQIANGRUO)
        _ns_in_place(res, "shengxiao", NS_SHENGXIAO)

        if isinstance(res.get("geju"), list):
            res["geju"] = _ns_list_in_place(res["geju"], NS_GEJU)

        # rizhu is a dict reference into zhu_list; it has already been processed above.

    def add_gan_info(self, gan: BaziChartGan, target: Dict):
        target["name"] = gan._gan.name
        target["wuxing"] = gan._wuxing.name
        target["yinyang"] = gan._gan.yinyang.name
        target["shishen"] = gan._shishen.name

    def add_zhi_info(self, zhi: BaziChartZhi, target: Dict):
        target["name"] = zhi._zhi.name
        target["wuxing"] = zhi._wuxing.name
        target["yinyang"] = zhi._zhi.yinyang.name
        hidden_gans = zhi._hidden_gans
        hidden_gans_shishen = zhi._hidden_gans_shishen_list
        target["hidden_gans"] = []
        for i in range(len(hidden_gans)):
            hidden_gans_item = dict()
            gan = hidden_gans[i]
            hidden_gans_item["name"] = gan.name
            hidden_gans_item["wuxing"] = gan.wuxing.name
            hidden_gans_item["yinyang"] = gan.yinyang.name
            shishen = hidden_gans_shishen[i]
            hidden_gans_item["shishen"] = shishen.name
            target["hidden_gans"].append(hidden_gans_item)

    def log_bazi_chart(self):
        currentDateAndTime = datetime.now()
        self.log_helper.info(
            f"【当前测算时间为】：{currentDateAndTime.year}年{currentDateAndTime.month}月{currentDateAndTime.day}日{currentDateAndTime.hour}时{currentDateAndTime.minute}分\n")
        self.log_helper.info("【八字原命盘】：\n")
        self.log_helper.info(f"年柱：{self.bazi_chart.year_zhu.chinese_name}\n")
        self.log_helper.info(f"月柱：{self.bazi_chart.month_zhu.chinese_name}\n")
        self.log_helper.info(f"日柱：{self.bazi_chart.day_zhu.chinese_name}\n")
        if not (self.without_time):
            self.log_helper.info(f"时柱：{self.bazi_chart.hour_zhu.chinese_name}\n")
        else:
            self.log_helper.info(f"时柱未知\n")
        self.log_helper.info("性别：男\n" if self.gender == "male" else "性别：女\n")

        # 详细信息
        detailed_info = self.bazi_chart.detailed_info()
        self.log_helper.info(f"【详细信息】：\n{''.join(detailed_info)}")

    def run_analysis(self):
        # Step 1: HehuaAnalysis
        hehua_analysis = HehuaAnalysis(self.bazi_chart, self.log_helper)
        hehua_raw, hehua_results = hehua_analysis.analyse()
        self.analysis_results["hehua_analysis"] = hehua_results

        # Step 2: PowerAnalysis (depends on HehuaAnalysis results)
        # 将hehua_results字典转换为列表的列表格式（PowerTransformer期望的格式）
        # hehua_results是字典，格式为 {'类别名': [force列表]}
        # 需要转换为 [[所有forces合并的列表]] 格式
        force_list = []
        for force_cate, forces in hehua_results.items():
            if isinstance(forces, list):
                force_list.extend(forces)
        force_analysis_results = [force_list] if force_list else []  # 列表的列表格式
        
        power_analysis = PowerAnalysis(
            self.bazi_chart, self.log_helper, force_analysis_results
        )
        power_results = power_analysis.analyse()
        self.analysis_results["power_analysis"] = power_results

        # Step 3: XinghaiAnalyser (depends on HehuaAnalysis results)
        xinghai_analyser = XinghaiAnalyser(self.bazi_chart, self.log_helper)
        xinghai_results = xinghai_analyser.analyse()
        self.analysis_results["xinghai_analysis"] = xinghai_results

        # Step 4: ShenShaAnalyser (depends on HehuaAnalysis results)
        shensha_analyser = ShenShaAnalyser(self.bazi_chart, self.log_helper)
        shensha_results, self.analysis_results["shensha_sorted"] = shensha_analyser.analyse()
        self.analysis_results["shensha_analysis"] = shensha_results
        self.shensha_instances = shensha_analyser._shensha_instances

        # Step 5: GejuAnalyser (depends on HehuaAnalysis and ShenShaAnalyser results)
        # GejuAnalyser期望的是列表格式（所有forces的列表），不是列表的列表
        geju_force_list = []
        for force_cate, forces in hehua_results.items():
            if isinstance(forces, list):
                geju_force_list.extend(forces)
        
        geju_analyser = GejuAnalyser(
            self.bazi_chart, self.log_helper, geju_force_list, self.analysis_results["shensha_analysis"]
        )
        geju_results = geju_analyser.analyse()
        self.analysis_results["geju_analysis"] = geju_results

        # Step 6: ShishenAnalyser (depends on HehuaAnalysis and ShenShaAnalyser results)
        shishen_analyser = ShishenAnalyser(
            self.bazi_chart,
            self.log_helper,
            hehua_results,
            xinghai_results,
            shensha_results,
            geju_results,
            power_results
        )
        shishen_results = shishen_analyser.analyse()  # 修正此处
        self.analysis_results["shishen_analysis"] = shishen_results

        # Step 7 : Get ditiansui and qiongtongbaojian:
        self.guji = "【相关材料参考】："
        self.guji += (
            ditiansui_qiongtong_analysis(
                self.bazi_chart.day_gan.get().chinese_name,
                self.bazi_chart.month_zhi.get().chinese_name,
            )
        )
        self.log_helper.info(self.guji)

        self.log_helper.info(f"【配偶出生方向】：{self.bazi_chart.peiou_fangwei}")

        if self.bazi_chart.is_special:
            self.log_helper.info("【特殊命格相关材料参考】：")
            if self.bazi_chart.refer:
                # 最终结果汇总
                self.log_helper.info(
                    "原局可能是专旺格或从格，需要考虑的主要五行力量对应的天干与月令关系相关材料："
                )
                self.log_helper.info(
                    ditiansui_qiongtong_analysis(
                        self.bazi_chart.refer, self.bazi_chart.month_zhi.get().chinese_name
                    )
                )
            else:
                self.log_helper.info("原局可能是两气成象格。")

        # 最终结果汇总
        self.log_helper.debug("分析完成。")

    def get_analysis_summary(self) -> Tuple[str, str, str]:
        return self.log_helper.ans, self.liupan, self.guji

    def search_shensha_in_zhu(self, gan, zhi, chart):
        res = []
        for shensha in self.shensha_instances:
            if shensha.is_present_in_zhu(gan, zhi, chart):
                res.append(shensha.chinese_name)
        return res

    def search_shensha_enum_in_zhu(self, gan, zhi, chart):
        res = []
        for shensha in self.shensha_instances:
            if shensha.is_present_in_zhu(gan, zhi, chart):
                res.append(ShenshaEnum[shensha.__class__.__name__.upper()].value)
        return res

    # 规范化相关工作已下沉到 BaziChart 层，避免在 Frame 层做字典映射/清洗

    def find_yun_liu_nian_liuyue(self, target_year):
        """
        定位某个 target_year 对应的大运/流年/流月（文本返回，用于直接展示）。

        注意：本方法不是“枚举化 JSON API”，而是给人读的文本，因此这里会把结构化的
        `gan_relation` / `zhi_relation` 简化为字符串描述。

        Returns:
            str | None:
              - 命中：文本字符串
              - 未命中：None
        """
        def _fmt_ganzhi(gan_name: str, zhi_name: str) -> str:
            try:
                return Gan[strip_ns(gan_name)].chinese_name + Zhi[strip_ns(zhi_name)].chinese_name
            except Exception:
                return f"{gan_name}{zhi_name}"

        def _fmt_shishen(ss_name: str) -> str:
            try:
                return Shishen[strip_ns(ss_name)].chinese_name
            except Exception:
                return ss_name

        def _fmt_relations(relations) -> str:
            if not relations:
                return ""
            parts = []
            for r in relations:
                if isinstance(r, dict):
                    t = strip_ns(r.get("type", ""))
                    members = r.get("members", [])
                    if isinstance(members, list):
                        members_s = ",".join([strip_ns(m) for m in members])
                    else:
                        members_s = str(members)
                    parts.append(f"{t}({members_s})" if t else members_s)
                else:
                    parts.append(str(r))
            return "，".join([p for p in parts if p])

        idx = 0
        word = ""
        for yun in self.res.get("yun", []):
            for nian in yun.get("liunian", []):
                if nian.get("year") == target_year:
                    if idx > 0:
                        dayun_gz = _fmt_ganzhi(yun.get("gan", ""), yun.get("zhi", ""))
                        dayun_ss = _fmt_shishen(yun.get("gan_shishen", "")) + _fmt_shishen(yun.get("zhi_shishen", ""))
                        word += f"所在大运：{dayun_gz}【{dayun_ss}】"

                        dayun_shensha = [strip_ns(x) for x in (yun.get("shensha", []) or [])]
                        dayun_rel = _fmt_relations((yun.get("gan_relation", []) or []) + (yun.get("zhi_relation", []) or []))
                        if dayun_shensha or dayun_rel:
                            word += "("
                            if dayun_shensha:
                                word += f"神煞【{dayun_shensha}】"
                            if dayun_rel:
                                word += f"关系【{dayun_rel}】"
                            word += ")"

                    nian_gz = _fmt_ganzhi(nian.get("gan", ""), nian.get("zhi", ""))
                    nian_ss = _fmt_shishen(nian.get("gan_shishen", "")) + _fmt_shishen(nian.get("zhi_shishen", ""))
                    word += f"目标流年：{nian.get('year')}{nian_gz}【{nian_ss}】{nian.get('age')}岁"

                    nian_shensha = [strip_ns(x) for x in (nian.get("shensha", []) or [])]
                    nian_rel = _fmt_relations((nian.get("gan_relation", []) or []) + (nian.get("zhi_relation", []) or []))
                    if nian_shensha or nian_rel:
                        word += "("
                        if nian_shensha:
                            word += f"神煞【{nian_shensha}】"
                        if nian_rel:
                            word += f"关系【{nian_rel}】"
                        word += ")\n流月："

                    for yue in nian.get("liuyue", []):
                        yue_gz = _fmt_ganzhi(yue.get("gan", ""), yue.get("zhi", ""))
                        yue_ss = _fmt_shishen(yue.get("gan_shishen", "")) + _fmt_shishen(yue.get("zhi_shishen", ""))
                        word += f"{yue_gz}【{yue_ss}】"
                        yue_rel = _fmt_relations((yue.get("gan_relation", []) or []) + (yue.get("zhi_relation", []) or []))
                        if yue_rel:
                            word += f"(关系【{yue_rel}】)"
                    return word
            idx += 1
        return None

    def query_shensha_for_datetime(self, year, month, day, hour=None):
        """
        查询指定年月日时包含的神煞
        
        Args:
            year (int): 年份
            month (int): 月份
            day (int): 日期
            hour (int, optional): 小时，如果为None则不包含时柱
            
        Returns:
            dict: 包含各柱神煞信息的字典
        """
        from lunar_python import Lunar
        
        # 创建指定日期的农历对象
        lunar = Lunar.fromYmdHms(year, month, day, hour or 0, 0, 0)
        
        # 获取八字信息
        bazi = lunar.getBaZi()  # ['乙巳', '甲申', '丙子', '戊子']
        # print(f"Debug: bazi = {bazi}")
        # print(f"Debug: len(bazi) = {len(bazi)}")
        
        # 解析天干地支
        year_gan, year_zhi = bazi[0][0], bazi[0][1]
        month_gan, month_zhi = bazi[1][0], bazi[1][1]
        day_gan, day_zhi = bazi[2][0], bazi[2][1]
        hour_gan, hour_zhi = (bazi[3][0], bazi[3][1]) if hour is not None and len(bazi) > 3 else (None, None)
        
        # 初始化结果字典（bazi 用枚举值结构化表示，避免编码问题）
        result = {
            # 使用 ISO 风格日期字符串，避免终端/环境编码导致中文年月显示异常
            "date": f"{year:04d}-{month:02d}-{day:02d}" + (f" {hour:02d}:00" if hour is not None else ""),
            "bazi": {
                "year": {"gan": ns(NS_GAN, Gan.from_chinese(year_gan).name), "zhi": ns(NS_ZHI, Zhi.from_chinese(year_zhi).name)},
                "month": {"gan": ns(NS_GAN, Gan.from_chinese(month_gan).name), "zhi": ns(NS_ZHI, Zhi.from_chinese(month_zhi).name)},
                "day": {"gan": ns(NS_GAN, Gan.from_chinese(day_gan).name), "zhi": ns(NS_ZHI, Zhi.from_chinese(day_zhi).name)},
                "hour": (
                    {"gan": ns(NS_GAN, Gan.from_chinese(hour_gan).name), "zhi": ns(NS_ZHI, Zhi.from_chinese(hour_zhi).name)}
                    if hour is not None and len(bazi) > 3
                    else None
                ),
            },
            "shensha": {
                "year": [],
                "month": [],
                "day": [],
                "hour": []
            }
        }
        
        # 转换天干地支为Gan和Zhi对象
        year_gan_obj = Gan.from_chinese(year_gan)
        year_zhi_obj = Zhi.from_chinese(year_zhi)
        month_gan_obj = Gan.from_chinese(month_gan)
        month_zhi_obj = Zhi.from_chinese(month_zhi)
        day_gan_obj = Gan.from_chinese(day_gan)
        day_zhi_obj = Zhi.from_chinese(day_zhi)
        
        # 查询各柱的神煞
        result["shensha"]["year"] = [ns(NS_SHENSHA, x) for x in self.search_shensha_enum_in_zhu(year_gan_obj, year_zhi_obj, self.bazi_chart)]
        result["shensha"]["month"] = [ns(NS_SHENSHA, x) for x in self.search_shensha_enum_in_zhu(month_gan_obj, month_zhi_obj, self.bazi_chart)]
        result["shensha"]["day"] = [ns(NS_SHENSHA, x) for x in self.search_shensha_enum_in_zhu(day_gan_obj, day_zhi_obj, self.bazi_chart)]
        
        if hour is not None and len(bazi) > 3:
            hour_gan_obj = Gan.from_chinese(hour_gan)
            hour_zhi_obj = Zhi.from_chinese(hour_zhi)
            result["shensha"]["hour"] = [ns(NS_SHENSHA, x) for x in self.search_shensha_enum_in_zhu(hour_gan_obj, hour_zhi_obj, self.bazi_chart)]
        
        return result
    
    def format_shensha_query_result(self, result):
        """
        （内部工具方法，非对外 API）

        格式化 `query_shensha_for_datetime` 的返回结果为易读字符串，用于终端/调试展示。
        
        Args:
            result (dict): query_shensha_for_datetime方法的返回结果
            
        Returns:
            str: 格式化后的字符串
        """
        output = f"【{result['date']}神煞查询结果】\n"
        year_text = Gan[strip_ns(result["bazi"]["year"]["gan"])].chinese_name + Zhi[strip_ns(result["bazi"]["year"]["zhi"])].chinese_name
        month_text = Gan[strip_ns(result["bazi"]["month"]["gan"])].chinese_name + Zhi[strip_ns(result["bazi"]["month"]["zhi"])].chinese_name
        day_text = Gan[strip_ns(result["bazi"]["day"]["gan"])].chinese_name + Zhi[strip_ns(result["bazi"]["day"]["zhi"])].chinese_name
        output += f"八字：{year_text} {month_text} {day_text}"
        if result["bazi"]["hour"]:
            hour_text = Gan[strip_ns(result["bazi"]["hour"]["gan"])].chinese_name + Zhi[strip_ns(result["bazi"]["hour"]["zhi"])].chinese_name
            output += f" {hour_text}"
        output += "\n\n"
        
        # 年柱神煞
        output += f"年柱{year_text}："
        if result['shensha']['year']:
            output += f"神煞【{', '.join([strip_ns(x) for x in result['shensha']['year']])}】"
        else:
            output += "无神煞"
        output += "\n"
        
        # 月柱神煞
        output += f"月柱{month_text}："
        if result['shensha']['month']:
            output += f"神煞【{', '.join([strip_ns(x) for x in result['shensha']['month']])}】"
        else:
            output += "无神煞"
        output += "\n"
        
        # 日柱神煞
        output += f"日柱{day_text}："
        if result['shensha']['day']:
            output += f"神煞【{', '.join([strip_ns(x) for x in result['shensha']['day']])}】"
        else:
            output += "无神煞"
        output += "\n"
        
        # 时柱神煞（如果有）
        if result["bazi"]["hour"]:
            output += f"时柱{hour_text}："
            if result['shensha']['hour']:
                output += f"神煞【{', '.join([strip_ns(x) for x in result['shensha']['hour']])}】"
            else:
                output += "无神煞"
        return output
    
    def get_compatibility_analysis(self, other_chart: BaziChart) -> Dict[str, Any]:
        """
        分析两个命盘的神煞互涉，并返回指定格式的JSON
        
        Args:
            other_chart (BaziChart): 另一个命盘对象
            
        Returns:
            Dict: {
                "a_wang_b": [神煞名称列表, 去重],
                "b_wang_a": [神煞名称列表, 去重]
            }
        """
        shensha_analyser = ShenShaAnalyser(self.bazi_chart, self.log_helper)
        raw_results = shensha_analyser.analyse_compatibility(other_chart)
        
        a_has_b = raw_results['a_has_b_shensha']
        b_has_a = raw_results['b_has_a_shensha']
        
        # 提取神煞枚举并去重
        a_wang_b_names = sorted(list({ns(NS_SHENSHA, ShenshaEnum[item['name'].upper()].value) for item in a_has_b}))
        b_wang_a_names = sorted(list({ns(NS_SHENSHA, ShenshaEnum[item['name'].upper()].value) for item in b_has_a}))
        
        # 生肖合婚逻辑放在独立的 analyser 中，这里只调用
        shengxiao_hehun = ZodiacCompatibilityAnalyser(self.bazi_chart, other_chart).analyse()
        wuxing_vector = WuxingVectorCompatibilityAnalyser(self.bazi_chart, other_chart).analyse()

        wuxing_score = self._score_wuxing_vector(wuxing_vector)
        shensha_score = self._score_shensha(raw_results)
        shengxiao_score = self._score_shengxiao(shengxiao_hehun)
        overall_score = round((wuxing_score + shensha_score + shengxiao_score) / 3.0, 2)

        res = {
            "a_wang_b": a_wang_b_names,
            "b_wang_a": b_wang_a_names,
            "shengxiao_hehun": shengxiao_hehun,
            "wuxing_vector": wuxing_vector,
            "score": {
                "overall": overall_score,
                "components": {
                    "wuxing": wuxing_score,
                    "shensha": shensha_score,
                    "shengxiao": shengxiao_score,
                },
            },
        }

        self._namespace_compatibility_res(res)
        return res

    @staticmethod
    def _clamp_score(score: float) -> float:
        return max(0.0, min(100.0, score))

    def _score_wuxing_vector(self, wuxing_vector: dict) -> float:
        xiangsi = float(wuxing_vector.get("xiangsi_du", 0.0))
        hubu = float(wuxing_vector.get("hubu_du", 0.0))
        return round(self._clamp_score((xiangsi + hubu) / 2.0), 2)

    def _score_shengxiao(self, shengxiao_hehun: dict) -> float:
        relation = shengxiao_hehun.get("relation")
        if relation in {"LIUHE", "SANHE"}:
            return 80.0
        if relation in {"LIUCHONG", "LIUHAI"}:
            return 20.0
        return 50.0

    def _score_shensha(self, shensha: dict) -> float:
        positive = {
            "TIANYI",        # 天乙贵人
            "TIANYII",       # 天乙贵人（兼容历史命名）
            "TAIJIGUIREN",   # 太极贵人
            "TIANDEGUIREN",  # 天德贵人
            "YUEDE",         # 月德贵人
            "HONGLUAN",      # 红鸾
            "TIANXI",        # 天喜
            "TAOHUA",        # 桃花
        }
        negative = {
            "HONGYAN",   # 红艳煞
            "JIESHA",    # 劫煞
            "WANGSHEN",  # 亡神
            "GUCHEN",    # 孤辰
            "GUASU",     # 寡宿
        }
        items = shensha.get("a_has_b_shensha", []) + shensha.get("b_has_a_shensha", [])
        pos_count = 0
        neg_count = 0
        for item in items:
            name = str(item.get("name", "")).upper()
            if name in positive:
                pos_count += 1
            if name in negative:
                neg_count += 1

        score = 50.0 + 20.0 * pos_count - 20.0 * neg_count
        return round(self._clamp_score(score), 2)

    def _namespace_compatibility_res(self, res: dict) -> None:
        """对外合盘 JSON：把枚举字段统一转为 `NAMESPACE:CODE` 形式（原地修改）。"""
        sh = res.get("shengxiao_hehun")
        if not isinstance(sh, dict):
            return
        if "a_shengxiao" in sh:
            sh["a_shengxiao"] = ns(NS_SHENGXIAO, sh["a_shengxiao"])
        if "b_shengxiao" in sh:
            sh["b_shengxiao"] = ns(NS_SHENGXIAO, sh["b_shengxiao"])
        if "a_nianzhi" in sh:
            sh["a_nianzhi"] = ns(NS_ZHI, sh["a_nianzhi"])
        if "b_nianzhi" in sh:
            sh["b_nianzhi"] = ns(NS_ZHI, sh["b_nianzhi"])
        if "relation" in sh:
            sh["relation"] = ns(NS_ZODIAC_COMPAT_RELATION, sh["relation"])
        if "favorable" in sh:
            sh["favorable"] = ns(NS_ZODIAC_COMPAT_FAVORABILITY, sh["favorable"])
        if "detail" in sh:
            sh["detail"] = ns(NS_ZODIAC_COMPAT_DETAIL, sh["detail"])
    
    def query_shensha_impact_for_datetime(self, year, month, day, hour=None):
        """
        查询指定年月日时包含的神煞及其影响（每个神煞单独输出影响，不做总和统计）
        """
        from lunar_python import Lunar
        lunar = Lunar.fromYmdHms(year, month, day, hour or 0, 0, 0)
        bazi = lunar.getBaZi()
        year_gan, year_zhi = bazi[0][0], bazi[0][1]
        month_gan, month_zhi = bazi[1][0], bazi[1][1]
        day_gan, day_zhi = bazi[2][0], bazi[2][1]
        hour_gan, hour_zhi = (bazi[3][0], bazi[3][1]) if hour is not None and len(bazi) > 3 else (None, None)
        result = {
            # 使用 ISO 风格日期字符串，避免终端/环境编码导致中文年月显示异常
            "date": f"{year:04d}-{month:02d}-{day:02d}" + (f" {hour:02d}:00" if hour is not None else ""),
            "bazi": {
                "year": {"gan": ns(NS_GAN, Gan.from_chinese(year_gan).name), "zhi": ns(NS_ZHI, Zhi.from_chinese(year_zhi).name)},
                "month": {"gan": ns(NS_GAN, Gan.from_chinese(month_gan).name), "zhi": ns(NS_ZHI, Zhi.from_chinese(month_zhi).name)},
                "day": {"gan": ns(NS_GAN, Gan.from_chinese(day_gan).name), "zhi": ns(NS_ZHI, Zhi.from_chinese(day_zhi).name)},
                "hour": (
                    {"gan": ns(NS_GAN, Gan.from_chinese(hour_gan).name), "zhi": ns(NS_ZHI, Zhi.from_chinese(hour_zhi).name)}
                    if hour is not None and len(bazi) > 3
                    else None
                ),
            },
            "shensha": {
                "year": [],
                "month": [],
                "day": [],
                "hour": []
            },
            "impact": {
                "year": [],
                "month": [],
                "day": [],
                "hour": []
            }
        }
        # 转换天干地支为Gan和Zhi对象
        year_gan_obj = Gan.from_chinese(year_gan)
        year_zhi_obj = Zhi.from_chinese(year_zhi)
        month_gan_obj = Gan.from_chinese(month_gan)
        month_zhi_obj = Zhi.from_chinese(month_zhi)
        day_gan_obj = Gan.from_chinese(day_gan)
        day_zhi_obj = Zhi.from_chinese(day_zhi)
        # 查询各柱的神煞
        year_shensha = [ns(NS_SHENSHA, x) for x in self.search_shensha_enum_in_zhu(year_gan_obj, year_zhi_obj, self.bazi_chart)]
        month_shensha = [ns(NS_SHENSHA, x) for x in self.search_shensha_enum_in_zhu(month_gan_obj, month_zhi_obj, self.bazi_chart)]
        day_shensha = [ns(NS_SHENSHA, x) for x in self.search_shensha_enum_in_zhu(day_gan_obj, day_zhi_obj, self.bazi_chart)]
        result["shensha"]["year"] = year_shensha
        result["shensha"]["month"] = month_shensha
        result["shensha"]["day"] = day_shensha
        if hour is not None and len(bazi) > 3:
            hour_gan_obj = Gan.from_chinese(hour_gan)
            hour_zhi_obj = Zhi.from_chinese(hour_zhi)
            hour_shensha = [ns(NS_SHENSHA, x) for x in self.search_shensha_enum_in_zhu(hour_gan_obj, hour_zhi_obj, self.bazi_chart)]
            result["shensha"]["hour"] = hour_shensha
        # 记录每个神煞的影响
        enum_to_instance = {
            ns(NS_SHENSHA, ShenshaEnum[s.__class__.__name__.upper()].value): s for s in self.shensha_instances
        }
        for pillar in ["year", "month", "day", "hour"]:
            for shensha_name in result["shensha"][pillar]:
                shensha_instance = enum_to_instance.get(shensha_name)
                if not shensha_instance:
                    continue
                # 只显示非零影响
                impact = {k: v for k, v in shensha_instance.impact.items() if v != 0}
                if impact:
                    result["impact"][pillar].append({
                        "name": shensha_name,
                        "impact": impact
                    })
        return result

    def format_shensha_impact_result(self, result):
        """
        （内部工具方法，非对外 API）

        格式化 `query_shensha_impact_for_datetime` 的返回结果为易读字符串（每个神煞单独输出影响）。
        """
        output = f"【{result['date']}神煞影响分析】\n"
        year_text = Gan[strip_ns(result["bazi"]["year"]["gan"])].chinese_name + Zhi[strip_ns(result["bazi"]["year"]["zhi"])].chinese_name
        month_text = Gan[strip_ns(result["bazi"]["month"]["gan"])].chinese_name + Zhi[strip_ns(result["bazi"]["month"]["zhi"])].chinese_name
        day_text = Gan[strip_ns(result["bazi"]["day"]["gan"])].chinese_name + Zhi[strip_ns(result["bazi"]["day"]["zhi"])].chinese_name
        output += f"八字：{year_text} {month_text} {day_text}"
        if result["bazi"]["hour"]:
            hour_text = Gan[strip_ns(result["bazi"]["hour"]["gan"])].chinese_name + Zhi[strip_ns(result["bazi"]["hour"]["zhi"])].chinese_name
            output += f" {hour_text}"
        output += "\n\n"
        # 显示神煞及其影响
        impact_names = {
            'career': '事业',
            'love': '爱情', 
            'study': '学业',
            'health': '健康',
            'life': '生活',
            'spirituality': '灵性',
            'interpersonal': '人际',
            'overall': '全能'
        }
        for pillar in ["year", "month", "day", "hour"]:
            pillar_name = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}[pillar]
            output += f"{pillar_name}：\n"
            if result['impact'][pillar]:
                for shensha in result['impact'][pillar]:
                    code = strip_ns(shensha.get("name"))
                    cn = None
                    if code:
                        try:
                            # 优先用已初始化的实例缓存
                            if hasattr(self, "_shensha_cn_cache") and self._shensha_cn_cache:
                                cn = self._shensha_cn_cache.get(code)
                        except Exception:
                            cn = None
                    output += f"  神煞：{cn or code or shensha.get('name')}\n"
                    for k, v in shensha['impact'].items():
                        output += f"    {impact_names[k]}：{v:+d}\n"
            else:
                output += "  无神煞\n"
            output += "\n"
        return output

    def get_daily_fortune_score(self, year: int, month: int, day: int, weights: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """
        计算指定日期的运势得分。

        Args:
            year, month, day: 目标日期
            weights: 喜忌权重字典，支持标准枚举键名（如 "WUXING:MU"）或中文键名。
                     格式示例：
                     {
                       "xi": {"WUXING:MU": 30, "WUXING:HUO": 20},
                       "ji": {"WUXING:JIN": 40}
                     }

        Returns:
            Dict: {
                "date": "YYYY-MM-DD",
                "score": 75.5
            }
        """
        # 1. 转换权重 Key 为内部使用的中文 Key
        # WUXING:MU -> "木"
        processed_weights = {"喜": {}, "忌": {}}
        
        # 映射表: Wuxing Enum Name -> Chinese Name
        wuxing_map = {
            "MU": "木", "HUO": "火", "TU": "土", "JIN": "金", "SHUI": "水"
        }

        def _process_weight_dict(input_dict):
            res = {}
            if not isinstance(input_dict, dict):
                return res
            for k, v in input_dict.items():
                # 处理键名，支持 "WUXING:MU", "MU", "木" 三种形式
                clean_key = strip_ns(k) # 去除 WUXING: 前缀
                chinese_key = wuxing_map.get(clean_key, clean_key) # 尝试转中文，如果转不了保留原样
                res[chinese_key] = v
            return res

        if "xi" in weights:
            processed_weights["喜"] = _process_weight_dict(weights.get("xi", {}))
        if "ji" in weights:
            processed_weights["忌"] = _process_weight_dict(weights.get("ji", {}))

        # 2. 调用分析器
        analyser = DailyFortuneAnalyser(self.bazi_chart, self.log_helper)
        score = analyser.analyse_daily_score(year, month, day, processed_weights)

        return {
            "date": f"{year:04d}-{month:02d}-{day:02d}",
            "score": score
        }
