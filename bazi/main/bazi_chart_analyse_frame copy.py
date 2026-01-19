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
import time
from datetime import datetime
from typing import Dict, Tuple

from ..analysis.ditiansui_qiongtong_analysis import ditiansui_qiongtong_analysis
from ..analysis.geju.geju_analyser import GejuAnalyser
from ..analysis.hehua.hehua_analysis import HehuaAnalysis
from ..analysis.power.power_analysis import PowerAnalysis
from ..analysis.shensha.shensha_analyser import ShenShaAnalyser
from ..analysis.shishen.shishen_analyser import ShishenAnalyser
from ..analysis.xinghai.xinghai_analyser import XinghaiAnalyser
from ..core.bazi_chart import BaziChart, BaziChartGan, BaziChartZhi
from ..core.property import Gan, Zhi, get_shengxiao_by_zhi_name
from ..utils.log_helper import LogHelper


class BaziChartAnalyseFrame:
    def __init__(self, lunar, gender, without_time=False, enable_terminal_output=True):
        # 记录开始执行时间
        self.start_time = time.time()
        
        self.res = dict()
        self.bazi_chart = BaziChart(lunar, gender, without_time)
        self.without_time = without_time
        self.analysis_results = {}
        self.log_helper = LogHelper(enable_terminal_output=enable_terminal_output)
        self.gender = gender
        self.liupan = ""
        self.guji = ""
        self.shensha_instances = []
        self.liunian_shensha = []
        # 记录八字原命盘
        self.log_bazi_chart()

    def run_shensha_analysis(self):
        """执行神煞分析"""
        shensha_analyser = ShenShaAnalyser(self.bazi_chart, self.log_helper)
        shensha_results, self.analysis_results["shensha_sorted"] = shensha_analyser.analyse()
        self.analysis_results["shensha_analysis"] = shensha_results
        self.shensha_instances = shensha_analyser._shensha_instances

    def generate_fast_res(self):

        # 执行神煞分析（快速结果需要）
        self.run_shensha_analysis()
        """生成快速结果，不包含五行、十神比例、身强身弱、格局、日主、生肖"""
        # 基础柱信息
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
        
        # 纳音、地支、旬空、起运等基本信息
        self.res["nayin"] = self.bazi_chart.nayin_list
        self.res["daygan_dishi"] = self.bazi_chart.dishi_list
        self.res["zizuo_dishi"] = self.bazi_chart.dishi_zizuo_list
        self.res["xunkong"] = self.bazi_chart.xunkong_list
        self.res["startyun"] = self.bazi_chart.start_yun
        
        # 神煞信息
        self.res["shensha"] = []
        for pos in self.analysis_results["shensha_sorted"]:
            shensha_name_list = [x['chinese_name'] for x in self.analysis_results["shensha_sorted"][pos]]
            self.res["shensha"].append({"values": shensha_name_list})
        
        # 大运流年流月信息
        self.res["yun"] = self.bazi_chart.dayun_liunian_liuyue_frontend_res
        
        # 生成JSON结果
        self.res_json = json.dumps(self.res)
        
        # 记录快速结果完成时间
        self.fast_res_time = time.time()
        fast_duration = self.fast_res_time - self.start_time
        self.log_helper.info(f"快速结果生成完成，耗时: {fast_duration:.4f} 秒")
        
        # 返回结果
        return self.res

    def generate_basic_res(self):
        # 先获取快速结果
        self.generate_fast_res()
        
        # 执行完整分析
        self.run_analysis()
        
        # 输出大运简排
        yun_idx = 0
        self.log_helper.info(f"【大运简排】：")
        for yun in self.res["yun"]:
            if yun_idx > 0:
                gan = Gan.from_chinese(yun["gan"])
                zhi = Zhi.from_chinese(yun["zhi"])
                yun["shensha"] = self.search_shensha_in_zhu(gan, zhi, self.bazi_chart)
                word = f'第{yun_idx}步运{yun["gan"]}{yun["zhi"]}【{yun["gan_shishen"]}{yun["zhi_shishen"]}】'
                self.log_helper.info(f'{yun["gan"]}{yun["zhi"]}{yun["year"]}')
                if len(yun["shensha"]) > 0 or (len(yun["gan_relation"]) + len(yun["zhi_relation"]) > 0):
                    word += '('
                    if len(yun["shensha"]) > 0:
                        word += f'神煞【{yun["shensha"]}】'
                    if len(yun["gan_relation"]) + len(yun["zhi_relation"]) > 0:
                        word += f'关系【{"，".join(yun["gan_relation"] + yun["zhi_relation"])}】'
                    word += ')'
                word += '：'
                self.liunian_shensha.append(word)
            else:
                self.liunian_shensha.append("起运前")
            yun_idx += 1
            for nian in yun["liunian"]:
                gan = Gan.from_chinese(nian["gan"])
                zhi = Zhi.from_chinese(nian["zhi"])
                nian["shensha"] = self.search_shensha_in_zhu(gan, zhi, self.bazi_chart)
                word = f'{nian["year"]}{nian["gan"]}{nian["zhi"]}【{nian["gan_shishen"]}{nian["zhi_shishen"]}】{nian["age"]}岁'
                if len(nian["shensha"]) > 0 or (len(nian["gan_relation"]) + len(nian["zhi_relation"]) > 0):
                    word += '('
                    if len(nian["shensha"]) > 0:
                        word += f'神煞【{nian["shensha"]}】'
                    if len(nian["gan_relation"]) + len(nian["zhi_relation"]) > 0:
                        word += f'关系【{"，".join(nian["gan_relation"] + nian["zhi_relation"])}】'
                    word += ')'
                word += '；'
                self.liunian_shensha.append(word)
        
        # 添加五行和十神比例信息
        self.res["wuxing_proportions"] = dict()
        for wuxing, proportion in self.analysis_results["power_analysis"].wuxing_proportions.items():
            self.res["wuxing_proportions"][wuxing.name] = proportion
        self.res["shishen_proportions"] = dict()
        for shishen, proportion in self.analysis_results["power_analysis"].shishen_proportions.items():
            self.res["shishen_proportions"][shishen.name] = proportion
        self.res["shenqiangshenruo"] = self.analysis_results["power_analysis"].shenqiangruo
        
        # 重新定义zhu_name_list变量（因为作用域问题）
        if self.without_time:
            zhu_name_list = ["year", "month", "day", "taiyuan", "minggong", "shengong"]
        else:
            zhu_name_list = ["year", "month", "day", "hour", "taiyuan", "minggong", "shengong"]
        
        self.res["rizhu"] = self.res["zhu_list"][zhu_name_list[2] + "_zhu"]["gan"]
        self.res["shengxiao"] = get_shengxiao_by_zhi_name(self.res["zhu_list"][zhu_name_list[0] + "_zhu"]["zhi"]["name"])
        if len(self.analysis_results["geju_analysis"]) == 1:
            self.res["geju"] = self.analysis_results["geju_analysis"][0]
        elif len(self.analysis_results["geju_analysis"]) > 1:
            self.res["geju"] = '，带'.join(self.analysis_results["geju_analysis"])
        else:
            self.res["geju"] = "需要进一步分析"
        self.res_json = json.dumps(self.res)
        # with open("output.txt", "w", encoding="utf-8") as file:
        #     file.write(self.res_json)
        # print(self.find_yun_liu_nian_liuyue(1998))

        # 大运流年
        dayun_liunian_info = self.liunian_shensha
        dayun_liunian_info_str = "\n".join(dayun_liunian_info)
        self.liupan = f"【流年大运排盘】：\n{dayun_liunian_info_str}"
        
        # 记录完整结果完成时间
        self.basic_res_time = time.time()
        basic_duration = self.basic_res_time - self.start_time
        fast_duration = self.fast_res_time - self.start_time
        additional_duration = self.basic_res_time - self.fast_res_time
        
        self.log_helper.info(f"完整结果生成完成，总耗时: {basic_duration:.4f} 秒")
        self.log_helper.info(f"快速结果耗时: {fast_duration:.4f} 秒")
        self.log_helper.info(f"额外分析耗时: {additional_duration:.4f} 秒")

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

    def add_gan_info(self, gan: BaziChartGan, target: Dict):
        target["name"] = gan._chinese_name
        target["wuxing"] = gan._wuxing.chinese_name
        target["yinyang"] = gan._yinyang
        target["shishen"] = gan._shishen.chinese_name

    def add_zhi_info(self, zhi: BaziChartZhi, target: Dict):
        target["name"] = zhi._chinese_name
        target["wuxing"] = zhi._wuxing.chinese_name
        target["yinyang"] = zhi._yinyang
        hidden_gans = zhi._hidden_gans
        hidden_gans_shishen = zhi._hidden_gans_shishen_list
        target["hidden_gans"] = []
        for i in range(len(hidden_gans)):
            hidden_gans_item = dict()
            gan = hidden_gans[i]
            hidden_gans_item["name"] = gan.chinese_name
            hidden_gans_item["wuxing"] = gan.wuxing.chinese_name
            hidden_gans_item["yinyang"] = gan.yinyang.chinese_name
            shishen = hidden_gans_shishen[i]
            hidden_gans_item["shishen"] = shishen.chinese_name
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
        power_analysis = PowerAnalysis(
            self.bazi_chart, self.log_helper, list(hehua_results.values())
        )
        power_results = power_analysis.analyse()
        self.analysis_results["power_analysis"] = power_results

        # Step 3: XinghaiAnalyser (depends on HehuaAnalysis results)
        xinghai_analyser = XinghaiAnalyser(self.bazi_chart, self.log_helper)
        xinghai_results = xinghai_analyser.analyse()
        self.analysis_results["xinghai_analysis"] = xinghai_results

        # Step 4: GejuAnalyser (depends on HehuaAnalysis and ShenShaAnalyser results)
        geju_analyser = GejuAnalyser(
            self.bazi_chart, self.log_helper, list(hehua_results.values()), self.analysis_results["shensha_analysis"]
        )
        geju_results = geju_analyser.analyse()
        self.analysis_results["geju_analysis"] = geju_results

        # Step 5: ShishenAnalyser (depends on HehuaAnalysis and ShenShaAnalyser results)
        shishen_analyser = ShishenAnalyser(
            self.bazi_chart,
            self.log_helper,
            hehua_results,
            xinghai_results,
            self.analysis_results["shensha_analysis"],
            geju_results,
            power_results
        )
        shishen_results = shishen_analyser.analyse()  # 修正此处
        self.analysis_results["shishen_analysis"] = shishen_results

        # Step 6 : Get ditiansui and qiongtongbaojian:
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

    def find_yun_liu_nian_liuyue(self, target_year):
        idx = 0
        word = ""
        for yun in self.res["yun"]:
            for nian in yun["liunian"]:
                if nian["year"] == target_year:
                    if idx > 0:
                        word += f'所在大运：{yun["gan"]}{yun["zhi"]}【{yun["gan_shishen"]}{yun["zhi_shishen"]}】'
                        if len(yun["shensha"]) > 0 or (len(yun["gan_relation"]) + len(yun["zhi_relation"]) > 0):
                            word += '('
                            if len(yun["shensha"]) > 0:
                                word += f'神煞【{yun["shensha"]}】'
                            if len(yun["gan_relation"]) + len(yun["zhi_relation"]) > 0:
                                word += f'关系【{"，".join(yun["gan_relation"] + yun["zhi_relation"])}】'
                            word += ')'
                    word += f'目标流年：{nian["year"]}{nian["gan"]}{nian["zhi"]}【{nian["gan_shishen"]}{nian["zhi_shishen"]}】{nian["age"]}岁(神煞【{nian["shensha"]}】'
                    if len(nian["shensha"]) > 0 or (len(nian["gan_relation"]) + len(nian["zhi_relation"]) > 0):
                        word += '('
                        if len(nian["shensha"]) > 0:
                            word += f'神煞【{nian["shensha"]}】'
                        if len(nian["gan_relation"]) + len(nian["zhi_relation"]) > 0:
                            word += f'关系【{"，".join(nian["gan_relation"] + nian["zhi_relation"])}】'
                        word += ')\n流月：'
                    for yue in nian["liuyue"]:
                        word += f'{yue["gan"]}{yue["zhi"]}【{yue["gan_shishen"]}{yue["zhi_shishen"]}】'
                        if len(yue["gan_relation"]) + len(yue["zhi_relation"]) > 0:
                            word += '('
                            if len(yue["gan_relation"]) + len(yue["zhi_relation"]) > 0:
                                word += f'关系【{"，".join(yue["gan_relation"] + yue["zhi_relation"])}】'
                            word += ')'
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
        
        # 初始化结果字典
        result = {
            "date": f"{year}年{month}月{day}日" + (f"{hour}时" if hour is not None else ""),
            "bazi": {
                "year": bazi[0],
                "month": bazi[1],
                "day": bazi[2],
                "hour": bazi[3] if hour is not None and len(bazi) > 3 else None
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
        result["shensha"]["year"] = self.search_shensha_in_zhu(year_gan_obj, year_zhi_obj, self.bazi_chart)
        result["shensha"]["month"] = self.search_shensha_in_zhu(month_gan_obj, month_zhi_obj, self.bazi_chart)
        result["shensha"]["day"] = self.search_shensha_in_zhu(day_gan_obj, day_zhi_obj, self.bazi_chart)
        
        if hour is not None and len(bazi) > 3:
            hour_gan_obj = Gan.from_chinese(hour_gan)
            hour_zhi_obj = Zhi.from_chinese(hour_zhi)
            result["shensha"]["hour"] = self.search_shensha_in_zhu(hour_gan_obj, hour_zhi_obj, self.bazi_chart)
        
        return result
    
    def format_shensha_query_result(self, result):
        """
        格式化神煞查询结果为易读的字符串
        
        Args:
            result (dict): query_shensha_for_datetime方法的返回结果
            
        Returns:
            str: 格式化后的字符串
        """
        output = f"【{result['date']}神煞查询结果】\n"
        output += f"八字：{result['bazi']['year']} {result['bazi']['month']} {result['bazi']['day']}"
        if result['bazi']['hour']:
            output += f" {result['bazi']['hour']}"
        output += "\n\n"
        
        # 年柱神煞
        output += f"年柱{result['bazi']['year']}："
        if result['shensha']['year']:
            output += f"神煞【{', '.join(result['shensha']['year'])}】"
        else:
            output += "无神煞"
        output += "\n"
        
        # 月柱神煞
        output += f"月柱{result['bazi']['month']}："
        if result['shensha']['month']:
            output += f"神煞【{', '.join(result['shensha']['month'])}】"
        else:
            output += "无神煞"
        output += "\n"
        
        # 日柱神煞
        output += f"日柱{result['bazi']['day']}："
        if result['shensha']['day']:
            output += f"神煞【{', '.join(result['shensha']['day'])}】"
        else:
            output += "无神煞"
        output += "\n"
        
        # 时柱神煞（如果有）
        if result['bazi']['hour']:
            output += f"时柱{result['bazi']['hour']}："
            if result['shensha']['hour']:
                output += f"神煞【{', '.join(result['shensha']['hour'])}】"
            else:
                output += "无神煞"
            output += "\n"
        
        return output
    
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
            "date": f"{year}年{month}月{day}日" + (f"{hour}时" if hour is not None else ""),
            "bazi": {
                "year": bazi[0],
                "month": bazi[1],
                "day": bazi[2],
                "hour": bazi[3] if hour is not None and len(bazi) > 3 else None
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
        year_shensha = self.search_shensha_in_zhu(year_gan_obj, year_zhi_obj, self.bazi_chart)
        month_shensha = self.search_shensha_in_zhu(month_gan_obj, month_zhi_obj, self.bazi_chart)
        day_shensha = self.search_shensha_in_zhu(day_gan_obj, day_zhi_obj, self.bazi_chart)
        result["shensha"]["year"] = year_shensha
        result["shensha"]["month"] = month_shensha
        result["shensha"]["day"] = day_shensha
        if hour is not None and len(bazi) > 3:
            hour_gan_obj = Gan.from_chinese(hour_gan)
            hour_zhi_obj = Zhi.from_chinese(hour_zhi)
            hour_shensha = self.search_shensha_in_zhu(hour_gan_obj, hour_zhi_obj, self.bazi_chart)
            result["shensha"]["hour"] = hour_shensha
        # 记录每个神煞的影响
        for pillar in ["year", "month", "day", "hour"]:
            for shensha_name in result["shensha"][pillar]:
                for shensha_instance in self.shensha_instances:
                    if shensha_instance.chinese_name == shensha_name:
                        # 只显示非零影响
                        impact = {k: v for k, v in shensha_instance.impact.items() if v != 0}
                        if impact:
                            result["impact"][pillar].append({
                                "name": shensha_name,
                                "impact": impact
                            })
                        break
        return result

    def format_shensha_impact_result(self, result):
        """
        格式化神煞影响查询结果为易读的字符串（每个神煞单独输出影响）
        """
        output = f"【{result['date']}神煞影响分析】\n"
        output += f"八字：{result['bazi']['year']} {result['bazi']['month']} {result['bazi']['day']}"
        if result['bazi']['hour']:
            output += f" {result['bazi']['hour']}"
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
                    output += f"  神煞：{shensha['name']}\n"
                    for k, v in shensha['impact'].items():
                        output += f"    {impact_names[k]}：{v:+d}\n"
            else:
                output += "  无神煞\n"
            output += "\n"
        return output
