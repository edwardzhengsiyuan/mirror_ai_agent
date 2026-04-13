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

# analysis/shensha/shensha.py

from ...core import Gan, Zhi

class Shensha:
    def __init__(self, source, shensha_type):
        self.source = source
        self.shensha_type = shensha_type
        # 初始化影响属性
        self.impact = {
            'career': 0,      # 事业
            'love': 0,        # 爱情
            'study': 0,       # 学业
            'health': 0,      # 健康
            'life': 0,        # 生活
            'spirituality': 0, # 灵性
            'interpersonal': 0, # 人际
            'overall': 0      # 全能
        }

    def is_present(self, chart):
        """判断神煞是否存在，子类需要实现此方法"""
        pass

    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        """判断神煞是否存在于某柱中，子类需要实现此方法"""
        pass

    @property
    def chinese_name(self):
        """返回神煞的中文名称，子类需要实现此方法"""
        pass

class Guchen(Shensha):
    def __init__(self):
        super().__init__(source='year_zhi', shensha_type='煞')
        self.impact = {
            'career': 0, 'love': -3, 'study': 0, 'health': 0,
            'life': -1, 'spirituality': 1, 'interpersonal': -2, 'overall': 0
        }

    @property
    def chinese_name(self):
        return "孤辰"

    def is_present(self, chart):
        guchen_map = {
            Zhi.HAI: Zhi.YIN, Zhi.ZI: Zhi.YIN, Zhi.CHOU: Zhi.YIN,
            Zhi.YIN: Zhi.SI, Zhi.MAO: Zhi.SI, Zhi.CHEN: Zhi.SI,
            Zhi.SI: Zhi.SHEN, Zhi.WU: Zhi.SHEN, Zhi.WEI: Zhi.SHEN,
            Zhi.SHEN: Zhi.HAI, Zhi.YOU: Zhi.HAI, Zhi.XU: Zhi.HAI
        }
        positions = []
        for i, zhi in enumerate(chart.zhi_list):
            if chart.year_zhi._zhi in guchen_map and guchen_map[chart.year_zhi._zhi] == zhi._zhi:
                positions.append(chart.zhu_list[i])
        word = "年支" + chart.year_zhi._zhi.chinese_name + "见" + guchen_map[chart.year_zhi._zhi].chinese_name + "为孤辰"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        guchen_map = {
            Zhi.HAI: Zhi.YIN, Zhi.ZI: Zhi.YIN, Zhi.CHOU: Zhi.YIN,
            Zhi.YIN: Zhi.SI, Zhi.MAO: Zhi.SI, Zhi.CHEN: Zhi.SI,
            Zhi.SI: Zhi.SHEN, Zhi.WU: Zhi.SHEN, Zhi.WEI: Zhi.SHEN,
            Zhi.SHEN: Zhi.HAI, Zhi.YOU: Zhi.HAI, Zhi.XU: Zhi.HAI
        }
        if chart.year_zhi._zhi in guchen_map and guchen_map[chart.year_zhi._zhi] == zhi_in:
            return True
        else:
            return False

class Guasu(Shensha):
    def __init__(self):
        super().__init__(source='year_zhi', shensha_type='煞')
        self.impact = {
            'career': 0, 'love': -3, 'study': 0, 'health': 0,
            'life': -1, 'spirituality': 1, 'interpersonal': -2, 'overall': 0
        }

    @property
    def chinese_name(self):
        return "寡宿"

    def is_present(self, chart):
        guasu_map = {
            Zhi.HAI: Zhi.XU, Zhi.ZI: Zhi.XU, Zhi.CHOU: Zhi.XU,
            Zhi.YIN: Zhi.CHOU, Zhi.MAO: Zhi.CHOU, Zhi.CHEN: Zhi.CHOU,
            Zhi.SI: Zhi.CHEN, Zhi.WU: Zhi.CHEN, Zhi.WEI: Zhi.CHEN,
            Zhi.SHEN: Zhi.WEI, Zhi.YOU: Zhi.WEI, Zhi.XU: Zhi.WEI
        }
        positions = []
        for i, zhi in enumerate(chart.zhi_list):
            if chart.year_zhi._zhi in guasu_map and guasu_map[chart.year_zhi._zhi ] == zhi._zhi:
                positions.append(chart.zhu_list[i])
        word = "年支" + chart.year_zhi._zhi.chinese_name + "见" + guasu_map[chart.year_zhi._zhi].chinese_name + "为寡宿"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        guasu_map = {
            Zhi.HAI: Zhi.XU, Zhi.ZI: Zhi.XU, Zhi.CHOU: Zhi.XU,
            Zhi.YIN: Zhi.CHOU, Zhi.MAO: Zhi.CHOU, Zhi.CHEN: Zhi.CHOU,
            Zhi.SI: Zhi.CHEN, Zhi.WU: Zhi.CHEN, Zhi.WEI: Zhi.CHEN,
            Zhi.SHEN: Zhi.WEI, Zhi.YOU: Zhi.WEI, Zhi.XU: Zhi.WEI
        }
        if chart.year_zhi._zhi in guasu_map and guasu_map[chart.year_zhi._zhi ] == zhi_in:
            return True
        else:
            return False

class Hongluan(Shensha):
    def __init__(self):
        super().__init__(source='year_zhi', shensha_type='神')
        self.impact = {
            'career': 0, 'love': 3, 'study': 0, 'health': 0,
            'life': 1, 'spirituality': 0, 'interpersonal': 1, 'overall': 0
        }

    @property
    def chinese_name(self):
        return "红鸾"

    def is_present(self, chart):
        hongluan_map = {
            Zhi.ZI: Zhi.MAO, Zhi.CHOU: Zhi.YIN, Zhi.YIN: Zhi.CHOU,
            Zhi.MAO: Zhi.ZI, Zhi.CHEN: Zhi.HAI, Zhi.SI: Zhi.XU,
            Zhi.WU: Zhi.YOU, Zhi.WEI: Zhi.SHEN, Zhi.SHEN: Zhi.WEI,
            Zhi.YOU: Zhi.WU, Zhi.XU: Zhi.SI, Zhi.HAI: Zhi.CHEN
        }
        positions = []
        for i, zhi in enumerate(chart.zhi_list):
            if chart.year_zhi._zhi in hongluan_map and hongluan_map[chart.year_zhi._zhi] == zhi._zhi:
                positions.append(chart.zhu_list[i])
        word = "年支" + chart.year_zhi._zhi.chinese_name + "见" + hongluan_map[chart.year_zhi._zhi].chinese_name + "为红鸾"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        hongluan_map = {
            Zhi.ZI: Zhi.MAO, Zhi.CHOU: Zhi.YIN, Zhi.YIN: Zhi.CHOU,
            Zhi.MAO: Zhi.ZI, Zhi.CHEN: Zhi.HAI, Zhi.SI: Zhi.XU,
            Zhi.WU: Zhi.YOU, Zhi.WEI: Zhi.SHEN, Zhi.SHEN: Zhi.WEI,
            Zhi.YOU: Zhi.WU, Zhi.XU: Zhi.SI, Zhi.HAI: Zhi.CHEN
        }
        if chart.year_zhi._zhi in hongluan_map and hongluan_map[chart.year_zhi._zhi] == zhi_in:
            return True
        else:
            return False

class Tianxi(Shensha):
    def __init__(self):
        super().__init__(source='year_zhi', shensha_type='神')
        self.impact = {
            'career': 0, 'love': 3, 'study': 0, 'health': 0,
            'life': 1, 'spirituality': 0, 'interpersonal': 1, 'overall': 0
        }

    @property
    def chinese_name(self):
        return "天喜"

    def is_present(self, chart):
        tianxi_map = {
            Zhi.ZI: Zhi.YOU, Zhi.CHOU: Zhi.SHEN, Zhi.YIN: Zhi.WEI,
            Zhi.MAO: Zhi.WU, Zhi.CHEN: Zhi.SI, Zhi.SI: Zhi.CHEN,
            Zhi.WU: Zhi.MAO, Zhi.WEI: Zhi.YIN, Zhi.SHEN: Zhi.CHOU,
            Zhi.YOU: Zhi.ZI, Zhi.XU: Zhi.HAI, Zhi.HAI: Zhi.XU
        }
        positions = []
        for i, zhi in enumerate(chart.zhi_list):
            if chart.year_zhi._zhi  in tianxi_map and tianxi_map[chart.year_zhi._zhi] == zhi._zhi:
                positions.append(chart.zhu_list[i])
        word = "年支" + chart.year_zhi._zhi.chinese_name + "见" + tianxi_map[chart.year_zhi._zhi].chinese_name + "为天喜"
        return positions, word    
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        tianxi_map = {
            Zhi.ZI: Zhi.YOU, Zhi.CHOU: Zhi.SHEN, Zhi.YIN: Zhi.WEI,
            Zhi.MAO: Zhi.WU, Zhi.CHEN: Zhi.SI, Zhi.SI: Zhi.CHEN,
            Zhi.WU: Zhi.MAO, Zhi.WEI: Zhi.YIN, Zhi.SHEN: Zhi.CHOU,
            Zhi.YOU: Zhi.ZI, Zhi.XU: Zhi.HAI, Zhi.HAI: Zhi.XU
        }
        if chart.year_zhi._zhi in tianxi_map and tianxi_map[chart.year_zhi._zhi] == zhi_in:
            return True
        else:
            return False

class Tiandeguiren(Shensha):
    def __init__(self):
        super().__init__(source='month_zhi', shensha_type='神')
        self.impact = {
            'career': 2,
            'love': 0,
            'study': 2,
            'health': 0,
            'life': 0,
            'spirituality': 0,
            'interpersonal': 2,
            'overall': 2
        }

    @property
    def chinese_name(self):
        return "天德贵人"

    def is_present(self, chart):
        month_to_tiande = {
            Zhi.YIN: [Gan.DING], Zhi.MAO: [Zhi.SHEN], Zhi.CHEN: [Gan.REN],
            Zhi.SI: [Gan.XIN], Zhi.WU: [Zhi.HAI], Zhi.WEI: [Gan.JIA],
            Zhi.SHEN: [Gan.GUI], Zhi.YOU: [Zhi.YIN], Zhi.XU: [Gan.BING],
            Zhi.HAI: [Gan.YI], Zhi.ZI: [Zhi.SI], Zhi.CHOU: [Gan.GENG]
        }
        positions = []
        month_zhi = chart.month_zhi._zhi
        if month_zhi in month_to_tiande:
            for tiande in month_to_tiande[month_zhi]:
                if isinstance(tiande, Gan):
                    for i, gan in enumerate(chart.gan_list):
                        if gan._gan == tiande:
                            positions.append(chart.zhu_list[i])
                elif isinstance(tiande, Zhi):
                    for i, zhi in enumerate(chart.zhi_list):
                        if zhi._zhi == tiande:
                            positions.append(chart.zhu_list[i])
        word = "月支" + chart.month_zhi._zhi.chinese_name + "见" + "".join([x.chinese_name for x in month_to_tiande[chart.month_zhi._zhi]]) + "为天德"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        month_to_tiande = {
            Zhi.YIN: [Gan.DING], Zhi.MAO: [Zhi.SHEN], Zhi.CHEN: [Gan.REN],
            Zhi.SI: [Gan.XIN], Zhi.WU: [Zhi.HAI], Zhi.WEI: [Gan.JIA],
            Zhi.SHEN: [Gan.GUI], Zhi.YOU: [Zhi.YIN], Zhi.XU: [Gan.BING],
            Zhi.HAI: [Gan.YI], Zhi.ZI: [Zhi.SI], Zhi.CHOU: [Gan.GENG]
        }
        month_zhi = chart.month_zhi._zhi
        if month_zhi in month_to_tiande:
            for tiande in month_to_tiande[month_zhi]:
                if tiande == gan_in:
                    return True
                elif tiande == zhi_in:
                    return True
        else:
            return False

class Yuede(Shensha):
    def __init__(self):
        super().__init__(source='month_zhi', shensha_type='神')
        self.impact = {
            'career': 2,
            'love': 0,
            'study': 2,
            'health': 0,
            'life': 0,
            'spirituality': 0,
            'interpersonal': 2,
            'overall': 2
        }

    @property
    def chinese_name(self):
        return "月德贵人"

    def is_present(self, chart):
        month_to_yuede = {
            Zhi.YIN: Gan.BING, Zhi.WU: Gan.BING, Zhi.XU: Gan.BING,
            Zhi.SHEN: Gan.REN, Zhi.ZI: Gan.REN, Zhi.CHEN: Gan.REN,
            Zhi.HAI: Gan.JIA, Zhi.MAO: Gan.JIA, Zhi.WEI: Gan.JIA,
            Zhi.SI: Gan.GENG, Zhi.YOU: Gan.GENG, Zhi.CHOU: Gan.GENG
        }
        positions = []
        month_zhi = chart.month_zhi._zhi
        if month_zhi in month_to_yuede:
            for i, gan in enumerate(chart.gan_list):
                if month_to_yuede[month_zhi] == gan._gan:
                    positions.append(chart.zhu_list[i])
        word = "月支" + chart.month_zhi._zhi.chinese_name + "见" + month_to_yuede[chart.month_zhi._zhi].chinese_name + "为月德"
        return positions, word  
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        month_to_yuede = {
            Zhi.YIN: Gan.BING, Zhi.WU: Gan.BING, Zhi.XU: Gan.BING,
            Zhi.SHEN: Gan.REN, Zhi.ZI: Gan.REN, Zhi.CHEN: Gan.REN,
            Zhi.HAI: Gan.JIA, Zhi.MAO: Gan.JIA, Zhi.WEI: Gan.JIA,
            Zhi.SI: Gan.GENG, Zhi.YOU: Gan.GENG, Zhi.CHOU: Gan.GENG
        }
        month_zhi = chart.month_zhi._zhi
        if month_zhi in month_to_yuede:
            if month_to_yuede[month_zhi] == gan_in:
                return True
        else:
            return False

class Tianyi(Shensha):
    def __init__(self):
        super().__init__(source='day_gan', shensha_type='神')
        self.impact = {
            'career': 3,
            'love': 0,
            'study': 3,
            'health': 2,
            'life': 0,
            'spirituality': 1,
            'interpersonal': 2,
            'overall': 3
        }

    @property
    def chinese_name(self):
        return "天乙贵人"

    def is_present(self, chart):
        day_gan_to_tianyi = {
            Gan.JIA: [Zhi.CHOU, Zhi.WEI], Gan.YI: [Zhi.ZI, Zhi.SHEN],
            Gan.BING: [Zhi.YOU, Zhi.HAI], Gan.DING: [Zhi.YOU, Zhi.HAI],
            Gan.WU: [Zhi.CHOU, Zhi.WEI], Gan.JI: [Zhi.ZI, Zhi.SHEN],
            Gan.GENG: [Zhi.YIN, Zhi.WU], Gan.XIN: [Zhi.YIN, Zhi.WU],
            Gan.REN: [Zhi.MAO, Zhi.SI], Gan.GUI: [Zhi.MAO, Zhi.SI]
        }
        positions = []
        day_gan = chart.day_gan._gan
        if day_gan in day_gan_to_tianyi:
            for i, zhi in enumerate(chart.zhi_list):
                if zhi._zhi in day_gan_to_tianyi[day_gan]:
                    positions.append(chart.zhu_list[i])
        word = "日干" + chart.day_gan._gan.chinese_name + "见" + "".join([x.chinese_name for x in day_gan_to_tianyi[chart.day_gan._gan]]) + "为天乙"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        day_gan_to_tianyi = {
            Gan.JIA: [Zhi.CHOU, Zhi.WEI], Gan.YI: [Zhi.ZI, Zhi.SHEN],
            Gan.BING: [Zhi.YOU, Zhi.HAI], Gan.DING: [Zhi.YOU, Zhi.HAI],
            Gan.WU: [Zhi.CHOU, Zhi.WEI], Gan.JI: [Zhi.ZI, Zhi.SHEN],
            Gan.GENG: [Zhi.YIN, Zhi.WU], Gan.XIN: [Zhi.YIN, Zhi.WU],
            Gan.REN: [Zhi.MAO, Zhi.SI], Gan.GUI: [Zhi.MAO, Zhi.SI]
        }
        day_gan = chart.day_gan._gan
        if day_gan in day_gan_to_tianyi:
            if zhi_in in day_gan_to_tianyi[day_gan]:
                return True
        else:
            return False

class Wenchang(Shensha):
    def __init__(self):
        super().__init__(source='day_gan', shensha_type='神')
        self.impact = {
            'career': 2,
            'love': 0,
            'study': 3,
            'health': 0,
            'life': 0,
            'spirituality': 1,
            'interpersonal': 0,
            'overall': 2
        }

    @property
    def chinese_name(self):
        return "文昌贵人"

    def is_present(self, chart):
        day_gan_to_wenchang = {
            Gan.JIA: Zhi.SI, Gan.YI: Zhi.WU, Gan.BING: Zhi.SHEN,
            Gan.DING: Zhi.YOU, Gan.WU: Zhi.SHEN, Gan.JI: Zhi.YOU,
            Gan.GENG: Zhi.HAI, Gan.XIN: Zhi.ZI, Gan.REN: Zhi.YIN,
            Gan.GUI: Zhi.MAO
        }
        positions = []
        day_gan = chart.day_gan._gan
        if day_gan in day_gan_to_wenchang:
            for i, zhi in enumerate(chart.zhi_list):
                if zhi._zhi == day_gan_to_wenchang[day_gan]:
                    positions.append(chart.zhu_list[i])
        word = "日干" + chart.day_gan._gan.chinese_name + "见" + day_gan_to_wenchang[chart.day_gan._gan].chinese_name + "为文昌"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        day_gan_to_wenchang = {
            Gan.JIA: Zhi.SI, Gan.YI: Zhi.WU, Gan.BING: Zhi.SHEN,
            Gan.DING: Zhi.YOU, Gan.WU: Zhi.SHEN, Gan.JI: Zhi.YOU,
            Gan.GENG: Zhi.HAI, Gan.XIN: Zhi.ZI, Gan.REN: Zhi.YIN,
            Gan.GUI: Zhi.MAO
        }
        day_gan = chart.day_gan._gan
        if day_gan in day_gan_to_wenchang:
            if zhi_in == day_gan_to_wenchang[day_gan]:
                return True
        else:
            return False

class Yangren(Shensha):
    def __init__(self):
        super().__init__(source='day_gan', shensha_type='煞')
        self.impact = {
            'career': -1,
            'love': -1,
            'study': 0,
            'health': -1,
            'life': -1,
            'spirituality': 0,
            'interpersonal': -1,
            'overall': -1
        }

    @property
    def chinese_name(self):
        return "羊刃"

    def is_present(self, chart):
        day_gan_to_yangren = {
            Gan.JIA: Zhi.MAO, Gan.BING: Zhi.WU, Gan.WU: Zhi.WU,
            Gan.GENG: Zhi.YOU, Gan.REN: Zhi.ZI
        }
        positions = []
        day_gan = chart.day_gan._gan
        if day_gan in day_gan_to_yangren:
            for i, zhi in enumerate(chart.zhi_list):
                if zhi._zhi == day_gan_to_yangren[day_gan]:
                    positions.append(chart.zhu_list[i])
            word = "日干" + chart.day_gan._gan.chinese_name + "见" + day_gan_to_yangren[chart.day_gan._gan].chinese_name + "为羊刃"
        else:
            word = "原日干无羊刃"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        day_gan_to_yangren = {
            Gan.JIA: Zhi.MAO, Gan.BING: Zhi.WU, Gan.WU: Zhi.WU,
            Gan.GENG: Zhi.YOU, Gan.REN: Zhi.ZI
        }
        day_gan = chart.day_gan._gan
        if day_gan in day_gan_to_yangren:
            if zhi_in == day_gan_to_yangren[day_gan]:
                return True
        else:
            return False

class Lushen(Shensha):
    def __init__(self):
        super().__init__(source='day_gan', shensha_type='神')
        self.impact = {
            'career': 2,
            'love': 0,
            'study': 0,
            'health': 0,
            'life': 2,
            'spirituality': 0,
            'interpersonal': 0,
            'overall': 1,
        }

    @property
    def chinese_name(self):
        return "禄神"

    def is_present(self, chart):
        day_gan_to_lushen = {
            Gan.JIA: Zhi.YIN, Gan.YI: Zhi.MAO, Gan.BING: Zhi.SI,
            Gan.DING: Zhi.WU, Gan.WU: Zhi.SI, Gan.JI: Zhi.WU,
            Gan.GENG: Zhi.SHEN, Gan.XIN: Zhi.YOU, Gan.REN: Zhi.HAI,
            Gan.GUI: Zhi.ZI
        }
        positions = []
        day_gan = chart.day_gan._gan
        if day_gan in day_gan_to_lushen:
            for i, zhi in enumerate(chart.zhi_list):
                if zhi._zhi == day_gan_to_lushen[day_gan]:
                    positions.append(chart.zhu_list[i])
        word = "日干" + chart.day_gan._gan.chinese_name + "见" + day_gan_to_lushen[chart.day_gan._gan].chinese_name + "为禄神"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        day_gan_to_lushen = {
            Gan.JIA: Zhi.YIN, Gan.YI: Zhi.MAO, Gan.BING: Zhi.SI,
            Gan.DING: Zhi.WU, Gan.WU: Zhi.SI, Gan.JI: Zhi.WU,
            Gan.GENG: Zhi.SHEN, Gan.XIN: Zhi.YOU, Gan.REN: Zhi.HAI,
            Gan.GUI: Zhi.ZI
        }
        day_gan = chart.day_gan._gan
        if day_gan in day_gan_to_lushen:
            if zhi_in == day_gan_to_lushen[day_gan]:
                return True
        else:
            return False

class Hongyan(Shensha):
    def __init__(self):
        super().__init__(source='day_gan', shensha_type='煞')
        self.impact = {
            'career': -1,
            'love': 2,
            'study': -1,
            'health': 0,
            'life': 1,
            'spirituality': 0,
            'interpersonal': 1,
            'overall': 0,
        }

    @property
    def chinese_name(self):
        return "红艳煞"

    def is_present(self, chart):
        day_gan_to_hongyan = {
            Gan.JIA: Zhi.WU, Gan.YI: Zhi.SHEN, Gan.BING: Zhi.YIN,
            Gan.DING: Zhi.WEI, Gan.WU: Zhi.CHEN, Gan.JI: Zhi.CHEN,
            Gan.GENG: Zhi.SHEN, Gan.XIN: Zhi.YOU, Gan.REN: Zhi.ZI,
            Gan.GUI: Zhi.XU
        }
        positions = []
        day_gan = chart.day_gan._gan
        if day_gan in day_gan_to_hongyan:
            for i, zhi in enumerate(chart.zhi_list):
                if zhi._zhi == day_gan_to_hongyan[day_gan]:
                    positions.append(chart.zhu_list[i])
        word = "日干" + chart.day_gan._gan.chinese_name + "见" + day_gan_to_hongyan[chart.day_gan._gan].chinese_name + "为红艳煞"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        day_gan_to_hongyan = {
            Gan.JIA: Zhi.WU, Gan.YI: Zhi.SHEN, Gan.BING: Zhi.YIN,
            Gan.DING: Zhi.WEI, Gan.WU: Zhi.CHEN, Gan.JI: Zhi.CHEN,
            Gan.GENG: Zhi.SHEN, Gan.XIN: Zhi.YOU, Gan.REN: Zhi.ZI,
            Gan.GUI: Zhi.XU
        }
        day_gan = chart.day_gan._gan
        if day_gan in day_gan_to_hongyan:
            if zhi_in == day_gan_to_hongyan[day_gan]:
                return True
        else:
            return False

class Jiangxing(Shensha):
    def __init__(self):
        super().__init__(source='day_zhi', shensha_type='神')
        self.impact = {
            'career': 1,
            'love': 0,
            'study': 0,
            'health': 0,
            'life': 0,
            'spirituality': 0,
            'interpersonal': 1,
            'overall': 0,
        }

    @property
    def chinese_name(self):
        return "将星"

    def is_present(self, chart):
        day_zhi_to_jiangxing = {
            Zhi.ZI: Zhi.YOU, Zhi.CHOU: Zhi.WU, Zhi.YIN: Zhi.MAO,
            Zhi.MAO: Zhi.ZI, Zhi.CHEN: Zhi.YOU, Zhi.SI: Zhi.WU,
            Zhi.WU: Zhi.MAO, Zhi.WEI: Zhi.ZI, Zhi.SHEN: Zhi.YOU,
            Zhi.YOU: Zhi.WU, Zhi.XU: Zhi.MAO, Zhi.HAI: Zhi.ZI
        }
        positions = []
        day_zhi = chart.day_zhi._zhi
        if day_zhi in day_zhi_to_jiangxing:
            for i, zhi in enumerate(chart.zhi_list):
                if zhi._zhi == day_zhi_to_jiangxing[day_zhi]:
                    positions.append(chart.zhu_list[i])
        word = "日支" + chart.day_zhi._zhi.chinese_name + "见" + day_zhi_to_jiangxing[chart.day_zhi._zhi].chinese_name + "为将星"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        day_zhi_to_jiangxing = {
            Zhi.ZI: Zhi.YOU, Zhi.CHOU: Zhi.WU, Zhi.YIN: Zhi.MAO,
            Zhi.MAO: Zhi.ZI, Zhi.CHEN: Zhi.YOU, Zhi.SI: Zhi.WU,
            Zhi.WU: Zhi.MAO, Zhi.WEI: Zhi.ZI, Zhi.SHEN: Zhi.YOU,
            Zhi.YOU: Zhi.WU, Zhi.XU: Zhi.MAO, Zhi.HAI: Zhi.ZI
        }
        day_zhi = chart.day_zhi._zhi
        if day_zhi in day_zhi_to_jiangxing:
            if zhi_in == day_zhi_to_jiangxing[day_zhi]:
                return True
        else:
            return False

class Huagai(Shensha):
    def __init__(self):
        super().__init__(source='day_zhi', shensha_type='煞')
        self.impact = {
            'career': 1,
            'love': -2,
            'study': 2,
            'health': 0,
            'life': 0,
            'spirituality': 2,
            'interpersonal': -2,
            'overall': 0,
        }

    @property
    def chinese_name(self):
        return "华盖"

    def is_present(self, chart):
        day_zhi_to_huagai = {
            Zhi.ZI: Zhi.CHEN, Zhi.CHOU: Zhi.CHOU, Zhi.YIN: Zhi.XU,
            Zhi.MAO: Zhi.WEI, Zhi.CHEN: Zhi.CHEN, Zhi.SI: Zhi.CHOU,
            Zhi.WU: Zhi.XU, Zhi.WEI: Zhi.WEI, Zhi.SHEN: Zhi.CHEN,
            Zhi.YOU: Zhi.CHOU, Zhi.XU: Zhi.XU, Zhi.HAI: Zhi.WEI
        }
        positions = []
        day_zhi = chart.day_zhi._zhi
        if day_zhi in day_zhi_to_huagai:
            for i, zhi in enumerate(chart.zhi_list):
                if zhi._zhi == day_zhi_to_huagai[day_zhi] and i != 2:
                    positions.append(chart.zhu_list[i])
        word = "日支" + chart.day_zhi._zhi.chinese_name + "见" + day_zhi_to_huagai[chart.day_zhi._zhi].chinese_name + "为华盖"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        day_zhi_to_huagai = {
            Zhi.ZI: Zhi.CHEN, Zhi.CHOU: Zhi.CHOU, Zhi.YIN: Zhi.XU,
            Zhi.MAO: Zhi.WEI, Zhi.CHEN: Zhi.CHEN, Zhi.SI: Zhi.CHOU,
            Zhi.WU: Zhi.XU, Zhi.WEI: Zhi.WEI, Zhi.SHEN: Zhi.CHEN,
            Zhi.YOU: Zhi.CHOU, Zhi.XU: Zhi.XU, Zhi.HAI: Zhi.WEI
        }
        day_zhi = chart.day_zhi._zhi
        if day_zhi in day_zhi_to_huagai:
            if zhi_in == day_zhi_to_huagai[day_zhi]:
                return True
        else:
            return False

class Yima(Shensha):
    def __init__(self):
        super().__init__(source='day_zhi', shensha_type='中性神煞')
        self.impact = {
            'career': 1,
            'love': 0,
            'study': 0,
            'health': 0,
            'life': 0,
            'spirituality': 0,
            'interpersonal': 0,
            'overall': 0,
        }

    @property
    def chinese_name(self):
        return "驿马"

    def is_present(self, chart):
        day_zhi_to_yima = {
            Zhi.ZI: Zhi.YIN, Zhi.CHOU: Zhi.HAI, Zhi.YIN: Zhi.SHEN,
            Zhi.MAO: Zhi.SI, Zhi.CHEN: Zhi.YIN, Zhi.SI: Zhi.HAI,
            Zhi.WU: Zhi.SHEN, Zhi.WEI: Zhi.SI, Zhi.SHEN: Zhi.YIN,
            Zhi.YOU: Zhi.HAI, Zhi.XU: Zhi.SHEN, Zhi.HAI: Zhi.SI
        }
        positions = []
        day_zhi = chart.day_zhi._zhi
        if day_zhi in day_zhi_to_yima:
            for i, zhi in enumerate(chart.zhi_list):
                if zhi._zhi == day_zhi_to_yima[day_zhi]:
                    positions.append(chart.zhu_list[i])
        word = "日支" + chart.day_zhi._zhi.chinese_name + "见" + day_zhi_to_yima[chart.day_zhi._zhi].chinese_name + "为驿马"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        day_zhi_to_yima = {
            Zhi.ZI: Zhi.YIN, Zhi.CHOU: Zhi.HAI, Zhi.YIN: Zhi.SHEN,
            Zhi.MAO: Zhi.SI, Zhi.CHEN: Zhi.YIN, Zhi.SI: Zhi.HAI,
            Zhi.WU: Zhi.SHEN, Zhi.WEI: Zhi.SI, Zhi.SHEN: Zhi.YIN,
            Zhi.YOU: Zhi.HAI, Zhi.XU: Zhi.SHEN, Zhi.HAI: Zhi.SI
        }
        day_zhi = chart.day_zhi._zhi
        if day_zhi in day_zhi_to_yima:
            if zhi_in == day_zhi_to_yima[day_zhi]:
                return True
        else:
            return False

class Jiesha(Shensha):
    def __init__(self):
        super().__init__(source='day_zhi', shensha_type='中性神煞')
        self.impact = {
            'career': -2,
            'love': -1,
            'study': 0,
            'health': -2,
            'life': -2,
            'spirituality': 0,
            'interpersonal': -2,
            'overall': -2,
        }

    @property
    def chinese_name(self):
        return "劫煞"

    def is_present(self, chart):
        day_zhi_to_jiesha = {
            Zhi.ZI: Zhi.SI, Zhi.CHOU: Zhi.YIN, Zhi.YIN: Zhi.HAI,
            Zhi.MAO: Zhi.SHEN, Zhi.CHEN: Zhi.SI, Zhi.SI: Zhi.YIN,
            Zhi.WU: Zhi.HAI, Zhi.WEI: Zhi.SHEN, Zhi.SHEN: Zhi.SI,
            Zhi.YOU: Zhi.YIN, Zhi.XU: Zhi.HAI, Zhi.HAI: Zhi.SHEN
        }
        positions = []
        day_zhi = chart.day_zhi._zhi
        if day_zhi in day_zhi_to_jiesha:
            for i, zhi in enumerate(chart.zhi_list):
                if zhi._zhi == day_zhi_to_jiesha[day_zhi]:
                    positions.append(chart.zhu_list[i])
        word = "日支" + chart.day_zhi._zhi.chinese_name + "见" + day_zhi_to_jiesha[chart.day_zhi._zhi].chinese_name + "为劫煞"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        day_zhi_to_jiesha = {
            Zhi.ZI: Zhi.SI, Zhi.CHOU: Zhi.YIN, Zhi.YIN: Zhi.HAI,
            Zhi.MAO: Zhi.SHEN, Zhi.CHEN: Zhi.SI, Zhi.SI: Zhi.YIN,
            Zhi.WU: Zhi.HAI, Zhi.WEI: Zhi.SHEN, Zhi.SHEN: Zhi.SI,
            Zhi.YOU: Zhi.YIN, Zhi.XU: Zhi.HAI, Zhi.HAI: Zhi.SHEN
        }
        day_zhi = chart.day_zhi._zhi
        if day_zhi in day_zhi_to_jiesha:
            if zhi_in == day_zhi_to_jiesha[day_zhi]:
                return True
        else:
            return False

class Wangshen(Shensha):
    def __init__(self):
        super().__init__(source='day_zhi', shensha_type='煞')
        self.impact = {
            'career': -2,
            'love': -1,
            'study': 0,
            'health': -2,
            'life': -2,
            'spirituality': 0,
            'interpersonal': -2,
            'overall': -2,
        }

    @property
    def chinese_name(self):
        return "亡神"

    def is_present(self, chart):
        day_zhi_to_wangshen = {
            Zhi.ZI: Zhi.HAI, Zhi.CHOU: Zhi.SHEN, Zhi.YIN: Zhi.SI,
            Zhi.MAO: Zhi.YIN, Zhi.CHEN: Zhi.HAI, Zhi.SI: Zhi.SHEN,
            Zhi.WU: Zhi.SI, Zhi.WEI: Zhi.YIN, Zhi.SHEN: Zhi.HAI,
            Zhi.YOU: Zhi.SHEN, Zhi.XU: Zhi.SI, Zhi.HAI: Zhi.YIN
        }
        positions = []
        day_zhi = chart.day_zhi._zhi
        if day_zhi in day_zhi_to_wangshen:
            for i, zhi in enumerate(chart.zhi_list):
                if zhi._zhi == day_zhi_to_wangshen[day_zhi]:
                    positions.append(chart.zhu_list[i])
        word = "日支" + chart.day_zhi._zhi.chinese_name + "见" + day_zhi_to_wangshen[chart.day_zhi._zhi].chinese_name + "为亡神"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        day_zhi_to_wangshen = {
            Zhi.ZI: Zhi.HAI, Zhi.CHOU: Zhi.SHEN, Zhi.YIN: Zhi.SI,
            Zhi.MAO: Zhi.YIN, Zhi.CHEN: Zhi.HAI, Zhi.SI: Zhi.SHEN,
            Zhi.WU: Zhi.SI, Zhi.WEI: Zhi.YIN, Zhi.SHEN: Zhi.HAI,
            Zhi.YOU: Zhi.SHEN, Zhi.XU: Zhi.SI, Zhi.HAI: Zhi.YIN
        }
        day_zhi = chart.day_zhi._zhi
        if day_zhi in day_zhi_to_wangshen:
            if zhi_in == day_zhi_to_wangshen[day_zhi]:
                return True
        else:
            return False

class Taohua(Shensha):
    def __init__(self):
        super().__init__(source='day_zhi', shensha_type='中性神煞')
        self.impact = {
            'career': 0,
            'love': 3,
            'study': 0,
            'health': 0,
            'life': 2,
            'spirituality': 0,
            'interpersonal': 2,
            'overall': 0,
        }

    @property
    def chinese_name(self):
        return "桃花"

    def is_present(self, chart):
        day_zhi_to_taohua = {
            Zhi.ZI: Zhi.YOU, Zhi.CHOU: Zhi.WU, Zhi.YIN: Zhi.MAO,
            Zhi.MAO: Zhi.ZI, Zhi.CHEN: Zhi.YOU, Zhi.SI: Zhi.WU,
            Zhi.WU: Zhi.MAO, Zhi.WEI: Zhi.ZI, Zhi.SHEN: Zhi.YOU,
            Zhi.YOU: Zhi.WU, Zhi.XU: Zhi.MAO, Zhi.HAI: Zhi.ZI
        }
        positions = []
        day_zhi = chart.day_zhi._zhi
        if day_zhi in day_zhi_to_taohua:
            for i, zhi in enumerate(chart.zhi_list):
                if zhi._zhi == day_zhi_to_taohua[day_zhi]:
                    positions.append(chart.zhu_list[i])
        word = "日支" + chart.day_zhi._zhi.chinese_name + "见" + day_zhi_to_taohua[chart.day_zhi._zhi].chinese_name + "为桃花"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        day_zhi_to_taohua = {
            Zhi.ZI: Zhi.YOU, Zhi.CHOU: Zhi.WU, Zhi.YIN: Zhi.MAO,
            Zhi.MAO: Zhi.ZI, Zhi.CHEN: Zhi.YOU, Zhi.SI: Zhi.WU,
            Zhi.WU: Zhi.MAO, Zhi.WEI: Zhi.ZI, Zhi.SHEN: Zhi.YOU,
            Zhi.YOU: Zhi.WU, Zhi.XU: Zhi.MAO, Zhi.HAI: Zhi.ZI
        }
        day_zhi = chart.day_zhi._zhi
        if day_zhi in day_zhi_to_taohua:
            if zhi_in == day_zhi_to_taohua[day_zhi]:
                return True
        else:
            return False

class Taijiguiren(Shensha):
    def __init__(self):
        super().__init__(source='year_gan_or_day_gan', shensha_type='神')
        self.impact = {
            'career': 1,
            'love': 0,
            'study': 2,
            'health': 0,
            'life': 0,
            'spirituality': 3,
            'interpersonal': 0,
            'overall': 2,
        }

    @property
    def chinese_name(self):
        return "太极贵人"

    def is_present(self, chart):
        taijiguiren_map = {
            Gan.JIA: [Zhi.ZI, Zhi.WEI], Gan.YI: [Zhi.ZI, Zhi.WU],
            Gan.BING: [Zhi.MAO, Zhi.YOU], Gan.DING: [Zhi.MAO, Zhi.YOU],
            Gan.WU: [Zhi.CHEN, Zhi.XU, Zhi.CHOU, Zhi.WEI], Gan.JI: [Zhi.CHEN, Zhi.XU, Zhi.CHOU, Zhi.WEI],
            Gan.GENG: [Zhi.YIN, Zhi.HAI], Gan.XIN: [Zhi.YIN, Zhi.HAI],
            Gan.REN: [Zhi.SI, Zhi.SHEN], Gan.GUI: [Zhi.SI, Zhi.SHEN]
        }
        positions = []
        for gan in [chart.year_gan._gan, chart.day_gan._gan]:
            if gan in taijiguiren_map:
                if any(zhi in [x._zhi for x in chart.zhi_list] for zhi in taijiguiren_map[gan]):
                    for i, zhi in enumerate(chart.zhi_list):
                        if zhi._zhi in taijiguiren_map[gan]:
                            positions.append(chart.zhu_list[i])
        word = "年干" + chart.year_gan._gan.chinese_name + "见" + "".join([x.chinese_name for x in taijiguiren_map[chart.year_gan._gan]]) + "，或日干" + chart.day_gan._gan.chinese_name + "见" + "".join([x.chinese_name for x in taijiguiren_map[chart.day_gan._gan]]) + "为太极"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        taijiguiren_map = {
            Gan.JIA: [Zhi.ZI, Zhi.WEI], Gan.YI: [Zhi.ZI, Zhi.WU],
            Gan.BING: [Zhi.MAO, Zhi.YOU], Gan.DING: [Zhi.MAO, Zhi.YOU],
            Gan.WU: [Zhi.CHEN, Zhi.XU, Zhi.CHOU, Zhi.WEI], Gan.JI: [Zhi.CHEN, Zhi.XU, Zhi.CHOU, Zhi.WEI],
            Gan.GENG: [Zhi.YIN, Zhi.HAI], Gan.XIN: [Zhi.YIN, Zhi.HAI],
            Gan.REN: [Zhi.SI, Zhi.SHEN], Gan.GUI: [Zhi.SI, Zhi.SHEN]
        }
        for gan in [chart.year_gan._gan, chart.day_gan._gan]:
            if gan in taijiguiren_map:
                if zhi_in in taijiguiren_map[gan]:
                    return True
        else:
            return False

class Kongwang(Shensha):
    def __init__(self):
        super().__init__(source='day_zhi', shensha_type='煞')
        self.impact = {
            'career': 0,
            'love': 0,
            'study': 0,
            'health': 0,
            'life': 0,
            'spirituality': 1,
            'interpersonal': 0,
            'overall': -1,
        }

    @property
    def chinese_name(self):
        return "空亡"

    def is_present(self, chart):
        xunkong_zhi = {
            "戌亥": [Zhi.XU, Zhi.HAI], "申酉": [Zhi.SHEN, Zhi.YOU], 
            "午未": [Zhi.WU, Zhi.WEI], "辰巳": [Zhi.CHEN, Zhi.SI], 
            "寅卯": [Zhi.YIN, Zhi.MAO], "子丑": [Zhi.ZI, Zhi.CHOU]
        }
        kongwang = chart.lunar_eightchar.getDayXunKong()
        positions = []
        if kongwang in xunkong_zhi:
            for zhi in xunkong_zhi[kongwang]:
                for i, z in enumerate(chart.zhi_list):
                    if zhi == z._zhi:
                        positions.append(chart.zhu_list[i])
        word = "日柱旬空" + kongwang
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        xunkong_zhi = {
            "戌亥": [Zhi.XU, Zhi.HAI], "申酉": [Zhi.SHEN, Zhi.YOU], 
            "午未": [Zhi.WU, Zhi.WEI], "辰巳": [Zhi.CHEN, Zhi.SI], 
            "寅卯": [Zhi.YIN, Zhi.MAO], "子丑": [Zhi.ZI, Zhi.CHOU]
        }
        kongwang = chart.lunar_eightchar.getDayXunKong()
        if kongwang in xunkong_zhi:
            for xunkong_zhi in xunkong_zhi[kongwang]:
                if zhi_in == xunkong_zhi:
                    return True
        else:
            return False

# ---------------- 新增神煞类 BEGIN ----------------

class SanqiGuiren(Shensha):
    def __init__(self):
        super().__init__(source='all', shensha_type='贵人')
        self.impact = {
            'career': 0,
            'love': 0,
            'study': 0,
            'health': 0,
            'life': 0,
            'spirituality': 0,
            'interpersonal': 0,
            'overall': 3,
        }
    @property
    def chinese_name(self):
        return "三奇贵人"
    def is_present(self, chart):
        """
        三奇贵人查法：
        天上三奇：甲戊庚
        地下三奇：乙丙丁  
        人中三奇：壬癸辛
        必须是年月日或月日时严格按照顺序排列，不能乱序或倒序
        """
        # 三奇组合定义
        tian_shang = [Gan.JIA, Gan.WU, Gan.GENG]  # 天上三奇：甲戊庚
        di_xia = [Gan.YI, Gan.BING, Gan.DING]     # 地下三奇：乙丙丁
        ren_zhong = [Gan.REN, Gan.GUI, Gan.XIN]   # 人中三奇：壬癸辛
        
        # 获取四柱天干
        gan_list = [g._gan for g in chart.gan_list]
        found = []
        positions = []
        # 检查年月日三奇（前三个天干）
        if len(gan_list) >= 3:
            year_month_day = gan_list[:3]
            if year_month_day == tian_shang:
                found.append("天上三奇(年月日)")
                positions += chart.zhu_list[:3]
            elif year_month_day == di_xia:
                found.append("地下三奇(年月日)")
                positions += chart.zhu_list[:3]
            elif year_month_day == ren_zhong:
                found.append("人中三奇(年月日)")
                positions += chart.zhu_list[:3]
        # 检查月日时三奇（后三个天干，如果有时柱）
        if len(gan_list) >= 4:
            month_day_hour = gan_list[1:4]  # 月日时
            if month_day_hour == tian_shang:
                found.append("天上三奇(月日时)")
                positions += chart.zhu_list[1:4]
            elif month_day_hour == di_xia:
                found.append("地下三奇(月日时)")
                positions += chart.zhu_list[1:4]
            elif month_day_hour == ren_zhong:
                found.append("人中三奇(月日时)")
                positions += chart.zhu_list[1:4]
        # 去重
        positions = list(dict.fromkeys(positions))
        word = f"命局含：{'、'.join(found)}为三奇贵人" if found else "无三奇贵人"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        """
        三奇贵人不针对单个柱，而是针对整体组合
        """
        return False

class FuxingGuiren(Shensha):
    def __init__(self):
        super().__init__(source='year_gan_or_day_gan', shensha_type='贵人')
        self.impact = {
            'career': 1,
            'love': 0,
            'study': 0,
            'health': 1,
            'life': 0,
            'spirituality': 0,
            'interpersonal': 1,
            'overall': 1,
        }
    @property
    def chinese_name(self):
        return "福星贵人"
    def is_present(self, chart):
        # 福星贵人：年干或日干见特定地支
        positions = []
        # 检查年干
        for zhu in chart.zhu_list:
            if self.is_present_in_zhu(None, zhu.zhi._zhi, chart):
                positions.append(zhu)
        
        word = f"年干{chart.year_gan._gan.chinese_name}或日干{chart.day_gan._gan.chinese_name}见特定地支为福星贵人" if positions else "无福星贵人"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        # 福星贵人查法：以年干或日干为主
        # 凡甲丙两干见寅或子，乙癸两干见卯或丑，戊干见申，己干见未，
        # 丁干见亥，庚干见午，辛干见巳，壬干见辰是也
        mapping = {
            Gan.JIA: [Zhi.YIN, Zhi.ZI],    # 甲干见寅或子
            Gan.YI: [Zhi.MAO, Zhi.CHOU],   # 乙干见卯或丑
            Gan.BING: [Zhi.YIN, Zhi.ZI],   # 丙干见寅或子
            Gan.DING: [Zhi.HAI],           # 丁干见亥
            Gan.WU: [Zhi.SHEN],            # 戊干见申
            Gan.JI: [Zhi.WEI],             # 己干见未
            Gan.GENG: [Zhi.WU],            # 庚干见午
            Gan.XIN: [Zhi.SI],             # 辛干见巳
            Gan.REN: [Zhi.CHEN],           # 壬干见辰
            Gan.GUI: [Zhi.MAO, Zhi.CHOU]   # 癸干见卯或丑
        }
        # 在流年大运查询中，应该用原盘的年干或日干来查询
        # 检查年干
        if chart.year_gan._gan in mapping and zhi_in in mapping[chart.year_gan._gan]:
            return True
        # 检查日干
        if chart.day_gan._gan in mapping and zhi_in in mapping[chart.day_gan._gan]:
            return True
        return False

class Kuigang(Shensha):
    def __init__(self):
        super().__init__(source='day_zhu', shensha_type='贵人')
        self.impact = {
            'career': 1,
            'love': -1,
            'study': 0,
            'health': 0,
            'life': 0,
            'spirituality': 0,
            'interpersonal': -1,
            'overall': 0,
        }
    @property
    def chinese_name(self):
        return "魁罡"
    def is_present(self, chart):
        kuigang = [(Gan.REN, Zhi.CHEN), (Gan.GENG, Zhi.XU), (Gan.GENG, Zhi.CHEN), (Gan.WU, Zhi.XU)]
        if (chart.day_gan._gan, chart.day_zhi._zhi) in kuigang:
            return [chart.day_zhu], f"日柱{chart.day_gan._gan.chinese_name}{chart.day_zhi._zhi.chinese_name}为魁罡"
        return [], "无魁罡"
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        # 魁罡贵人只与原盘日柱有关，流年大运中不可能出现
        return False

class GuoyinGuiren(Shensha):
    def __init__(self):
        super().__init__(source='year_gan_or_day_gan', shensha_type='贵人')
        self.impact = {
            'career': 2,
            'love': 0,
            'study': 0,
            'health': 0,
            'life': 0,
            'spirituality': 0,
            'interpersonal': 0,
            'overall': 0,
        }
    @property
    def chinese_name(self):
        return "国印贵人"
    def is_present(self, chart):
        # 归属原则：年干或日干见对应地支时，国印贵人应加在该地支所在柱
        mapping = {
            Gan.JIA: Zhi.XU, Gan.YI: Zhi.HAI, Gan.BING: Zhi.CHOU, Gan.DING: Zhi.YIN,
            Gan.WU: Zhi.CHOU, Gan.JI: Zhi.YIN, Gan.GENG: Zhi.CHEN, Gan.XIN: Zhi.SI,
            Gan.REN: Zhi.WEI, Gan.GUI: Zhi.SHEN
        }
        found = []
        for gan, zhi in mapping.items():
            if (chart.year_gan._gan == gan or chart.day_gan._gan == gan):
                for i, zhi_obj in enumerate(chart.zhi_list):
                    if zhi_obj._zhi == zhi:
                        found.append(chart.zhu_list[i])
        word = f"国印贵人：{','.join([g.chinese_name for g in found])}" if found else "无国印贵人"
        return found, word
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        mapping = {
            Gan.JIA: Zhi.XU, Gan.YI: Zhi.HAI, Gan.BING: Zhi.CHOU, Gan.DING: Zhi.YIN,
            Gan.WU: Zhi.CHOU, Gan.JI: Zhi.YIN, Gan.GENG: Zhi.CHEN, Gan.XIN: Zhi.SI,
            Gan.REN: Zhi.WEI, Gan.GUI: Zhi.SHEN
        }
        return any((gan_in == gan and zhi_in == zhi) for gan, zhi in mapping.items())

class DexiuGuiren(Shensha):
    def __init__(self):
        super().__init__(source='month_zhi', shensha_type='贵人')
        self.impact = {
            'career': 1,
            'love': 0,
            'study': 0,
            'health': 0,
            'life': 0,
            'spirituality': 0,
            'interpersonal': 0,
            'overall': 1,
        }
    @property
    def chinese_name(self):
        return "德秀贵人"
    def is_present(self, chart, other_chart=None):
        """
        德秀贵人查法：
        寅午戌月, 丙丁为德, 戊癸为秀
        申子辰月, 壬癸戊己为德, 丙辛甲己为秀
        巳酉丑月, 庚辛为德, 乙庚为秀
        亥卯未月, 甲乙为德, 丁壬为秀
        以生月为主, 看四柱天干中有否

        chart: 己方盘，用于取月支定德秀规则。
        other_chart: 可选。若不为空则表示合盘——去对方盘里找贵人，用 chart 的月支定规则，在 other_chart 的四柱中查是否同时有德、有秀；返回的 positions 为对方盘中带德/秀的柱。
        """
        positions = []
        month_zhi = chart.month_zhi._zhi

        # 合盘时：规则用己方(chart)月支，四柱用对方(other_chart)
        check_chart = other_chart if other_chart is not None else chart
        all_gans = [check_chart.year_gan._gan, check_chart.month_gan._gan, check_chart.day_gan._gan]
        if hasattr(check_chart, 'hour_gan') and check_chart.hour_gan:
            all_gans.append(check_chart.hour_gan._gan)

        # 根据月支确定德秀天干
        de_gans = []
        xiu_gans = []
        if month_zhi in [Zhi.YIN, Zhi.WU, Zhi.XU]:
            de_gans = [Gan.BING, Gan.DING]
            xiu_gans = [Gan.WU, Gan.GUI]
        elif month_zhi in [Zhi.SHEN, Zhi.ZI, Zhi.CHEN]:
            de_gans = [Gan.REN, Gan.GUI, Gan.WU, Gan.JI]
            xiu_gans = [Gan.BING, Gan.XIN, Gan.JIA, Gan.JI]
        elif month_zhi in [Zhi.SI, Zhi.YOU, Zhi.CHOU]:
            de_gans = [Gan.GENG, Gan.XIN]
            xiu_gans = [Gan.YI, Gan.GENG]
        elif month_zhi in [Zhi.HAI, Zhi.MAO, Zhi.WEI]:
            de_gans = [Gan.JIA, Gan.YI]
            xiu_gans = [Gan.DING, Gan.REN]

        has_de = any(gan in all_gans for gan in de_gans)
        has_xiu = any(gan in all_gans for gan in xiu_gans)

        if has_de and has_xiu:
            found_de = [gan for gan in de_gans if gan in all_gans]
            found_xiu = [gan for gan in xiu_gans if gan in all_gans]
            for zhu in check_chart.zhu_list:
                if zhu.gan._gan in found_de or zhu.gan._gan in found_xiu:
                    positions.append(zhu)
            word = f"德秀贵人：德{','.join([g.chinese_name for g in found_de])}，秀{','.join([g.chinese_name for g in found_xiu])}"
        else:
            word = "无德秀贵人"

        return positions, word

    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        """
        检查单个柱是否包含德秀贵人
        这里简化处理，只要该柱的天干是德或秀之一就算
        """
        month_zhi = chart.month_zhi._zhi
        
        # 根据月支确定德秀天干
        de_gans = []  # 德的天干
        xiu_gans = []  # 秀的天干
        
        if month_zhi in [Zhi.YIN, Zhi.WU, Zhi.XU]:  # 寅午戌月
            de_gans = [Gan.BING, Gan.DING]  # 丙丁为德
            xiu_gans = [Gan.WU, Gan.GUI]    # 戊癸为秀
        elif month_zhi in [Zhi.SHEN, Zhi.ZI, Zhi.CHEN]:  # 申子辰月
            de_gans = [Gan.REN, Gan.GUI, Gan.WU, Gan.JI]  # 壬癸戊己为德
            xiu_gans = [Gan.BING, Gan.XIN, Gan.JIA, Gan.JI]  # 丙辛甲己为秀
        elif month_zhi in [Zhi.SI, Zhi.YOU, Zhi.CHOU]:  # 巳酉丑月
            de_gans = [Gan.GENG, Gan.XIN]  # 庚辛为德
            xiu_gans = [Gan.YI, Gan.GENG]  # 乙庚为秀
        elif month_zhi in [Zhi.HAI, Zhi.MAO, Zhi.WEI]:  # 亥卯未月
            de_gans = [Gan.JIA, Gan.YI]    # 甲乙为德
            xiu_gans = [Gan.DING, Gan.REN] # 丁壬为秀
        
        return gan_in in de_gans or gan_in in xiu_gans

class Xuetang(Shensha):
    def __init__(self):
        super().__init__(source='year_nayin', shensha_type='神')
        self.impact = {
            'career': 1,
            'love': 0,
            'study': 3,
            'health': 0,
            'life': 0,
            'spirituality': 0,
            'interpersonal': 0,
            'overall': 0,
        }

    @property
    def chinese_name(self):
        return "学堂"

    def is_present(self, chart):
        """
        学堂查法：纳音之长生
        金命见巳，辛巳为正；
        木命见亥，己亥为正；
        水命见申，甲申为正；
        土命见申，戊申为正；
        火命见寅，丙寅为正。
        以年纳音查月日时支（禄命法）
        """
        # 年柱纳音与学堂地支的映射
        nayin_to_xuetang = {
            "海中金": [Zhi.SI, "辛巳"], "剑锋金": [Zhi.SI, "辛巳"], "白蜡金": [Zhi.SI, "辛巳"], 
            "沙中金": [Zhi.SI, "辛巳"], "金箔金": [Zhi.SI, "辛巳"], "钗钏金": [Zhi.SI, "辛巳"],
            "大林木": [Zhi.HAI, "己亥"], "杨柳木": [Zhi.HAI, "己亥"], "松柏木": [Zhi.HAI, "己亥"],
            "平地木": [Zhi.HAI, "己亥"], "桑柘木": [Zhi.HAI, "己亥"], "石榴木": [Zhi.HAI, "己亥"],
            "涧下水": [Zhi.SHEN, "甲申"], "泉中水": [Zhi.SHEN, "甲申"], "长流水": [Zhi.SHEN, "甲申"],
            "天河水": [Zhi.SHEN, "甲申"], "大溪水": [Zhi.SHEN, "甲申"], "大海水": [Zhi.SHEN, "甲申"],
            "屋上土": [Zhi.SHEN, "戊申"], "城头土": [Zhi.SHEN, "戊申"], "壁上土": [Zhi.SHEN, "戊申"],
            "大驿土": [Zhi.SHEN, "戊申"], "沙中土": [Zhi.SHEN, "戊申"], "路旁土": [Zhi.SHEN, "戊申"],
            "炉中火": [Zhi.YIN, "丙寅"], "山头火": [Zhi.YIN, "丙寅"], "霹雳火": [Zhi.YIN, "丙寅"],
            "山下火": [Zhi.YIN, "丙寅"], "覆灯火": [Zhi.YIN, "丙寅"], "天上火": [Zhi.YIN, "丙寅"]
        }
        
        found = []
        year_nayin = chart.year_nayin
        
        if year_nayin in nayin_to_xuetang:
            xuetang_zhi = nayin_to_xuetang[year_nayin][0]
            zheng_xuetang = nayin_to_xuetang[year_nayin][1]
            
            # 检查年、月、日、时支
            for i in range(0, len(chart.zhi_list)):
                zhi = chart.zhi_list[i]
                if zhi._zhi == xuetang_zhi:
                    # 检查是否为正学堂
                    zhu_gan = chart.gan_list[i]._gan.chinese_name
                    zhu_zhi = zhi._zhi.chinese_name
                    zhu_ganzhi = zhu_gan + zhu_zhi
                    
                    if zhu_ganzhi == zheng_xuetang:
                        found.append((chart.zhu_list[i], "正学堂"))
                    else:
                        found.append((chart.zhu_list[i], "学堂"))
        
        if found:
            xuetang_types = [f"{zhu.chinese_name}({xuetang_type})" for zhu, xuetang_type in found]
            word = f"学堂：{','.join(xuetang_types)}"
        else:
            word = "无学堂"
        
        return [zhu for zhu, _ in found], word

    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        nayin_to_xuetang = {
            "海中金": [Zhi.SI, "辛巳"], "剑锋金": [Zhi.SI, "辛巳"], "白蜡金": [Zhi.SI, "辛巳"], 
            "沙中金": [Zhi.SI, "辛巳"], "金箔金": [Zhi.SI, "辛巳"], "钗钏金": [Zhi.SI, "辛巳"],
            "大林木": [Zhi.HAI, "己亥"], "杨柳木": [Zhi.HAI, "己亥"], "松柏木": [Zhi.HAI, "己亥"],
            "平地木": [Zhi.HAI, "己亥"], "桑柘木": [Zhi.HAI, "己亥"], "石榴木": [Zhi.HAI, "己亥"],
            "涧下水": [Zhi.SHEN, "甲申"], "泉中水": [Zhi.SHEN, "甲申"], "长流水": [Zhi.SHEN, "甲申"],
            "天河水": [Zhi.SHEN, "甲申"], "大溪水": [Zhi.SHEN, "甲申"], "大海水": [Zhi.SHEN, "甲申"],
            "屋上土": [Zhi.SHEN, "戊申"], "城头土": [Zhi.SHEN, "戊申"], "壁上土": [Zhi.SHEN, "戊申"],
            "大驿土": [Zhi.SHEN, "戊申"], "沙中土": [Zhi.SHEN, "戊申"], "路旁土": [Zhi.SHEN, "戊申"],
            "炉中火": [Zhi.YIN, "丙寅"], "山头火": [Zhi.YIN, "丙寅"], "霹雳火": [Zhi.YIN, "丙寅"],
            "山下火": [Zhi.YIN, "丙寅"], "覆灯火": [Zhi.YIN, "丙寅"], "天上火": [Zhi.YIN, "丙寅"]
        }
        
        year_nayin = chart.year_nayin
        if year_nayin in nayin_to_xuetang:
            return zhi_in == nayin_to_xuetang[year_nayin][0]
        return False

class Ciguan(Shensha):
    def __init__(self):
        super().__init__(source='year_gan_or_day_gan', shensha_type='贵人')
        self.impact = {
            'career': 1,
            'love': 0,
            'study': 3,
            'health': 0,
            'life': 0,
            'spirituality': 0,
            'interpersonal': 0,
            'overall': 0,
        }

    @property
    def chinese_name(self):
        return "词馆"

    def is_present(self, chart):
        """
        词馆查法：以年干或日干为主
        甲干见庚寅, 乙干见辛卯, 丙干见乙巳, 丁干见戊午, 戊干见丁巳, 
        己干见庚午, 庚干见壬申, 辛干见癸酉, 壬干见癸亥, 癸干见壬戌.
        """
        # 天干与词馆干支的映射
        gan_to_ciguan = {
            Gan.JIA: ("庚", Zhi.YIN), Gan.YI: ("辛", Zhi.MAO), Gan.BING: ("乙", Zhi.SI),
            Gan.DING: ("戊", Zhi.WU), Gan.WU: ("丁", Zhi.SI), Gan.JI: ("庚", Zhi.WU),
            Gan.GENG: ("壬", Zhi.SHEN), Gan.XIN: ("癸", Zhi.YOU), Gan.REN: ("癸", Zhi.HAI),
            Gan.GUI: ("壬", Zhi.XU)
        }
        
        found = []
        # 检查年干和日干
        for gan in [chart.year_gan._gan, chart.day_gan._gan]:
            if gan in gan_to_ciguan:
                ciguan_gan_name, ciguan_zhi = gan_to_ciguan[gan]
                
                # 检查四柱中是否有对应的干支组合
                for i, zhu in enumerate(chart.zhu_list):
                    zhu_gan_name = chart.gan_list[i]._gan.chinese_name
                    zhu_zhi = chart.zhi_list[i]._zhi
                    
                    if zhu_gan_name == ciguan_gan_name and zhu_zhi == ciguan_zhi:
                        found.append(chart.zhu_list[i])
        
        if found:
            word = f"词馆：{','.join([zhu.chinese_name for zhu in found])}"
        else:
            word = "无词馆"
        
        return found, word

    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        gan_to_ciguan = {
            Gan.JIA: ("庚", Zhi.YIN), Gan.YI: ("辛", Zhi.MAO), Gan.BING: ("乙", Zhi.SI),
            Gan.DING: ("戊", Zhi.WU), Gan.WU: ("丁", Zhi.SI), Gan.JI: ("庚", Zhi.WU),
            Gan.GENG: ("壬", Zhi.SHEN), Gan.XIN: ("癸", Zhi.YOU), Gan.REN: ("癸", Zhi.HAI),
            Gan.GUI: ("壬", Zhi.XU)
        }
        
        # 检查年干和日干
        for gan in [chart.year_gan._gan, chart.day_gan._gan]:
            if gan in gan_to_ciguan:
                ciguan_gan_name, ciguan_zhi = gan_to_ciguan[gan]
                if gan_in.chinese_name == ciguan_gan_name and zhi_in == ciguan_zhi:
                    return True
        return False

class TianchuGuiren(Shensha):
    def __init__(self):
        super().__init__(source='year_gan_or_day_gan', shensha_type='贵人')
        self.impact = {
            'career': 1,
            'love': 0,
            'study': 0,
            'health': 0,
            'life': 2,
            'spirituality': 0,
            'interpersonal': 0,
            'overall': 0,
        }
    @property
    def chinese_name(self):
        return "天厨贵人"
    def is_present(self, chart):
        # 天厨贵人：以年干或日干为主，对应於年月日时地支
        positions = []
        # 检查所有柱
        for zhu in chart.zhu_list:
            if self.is_present_in_zhu(None, zhu.zhi._zhi, chart):
                positions.append(zhu)
        
        word = f"天厨贵人：{','.join([zhu.chinese_name for zhu in positions])}" if positions else "无天厨贵人"
        return positions, word
    
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        # 天厨贵人查法：以年干或日干为主，对应於年月日时地支
        # 凡甲干见巳，乙干见午，丙干见子，丁干见巳，戊干见午，己干见申，庚干见寅，辛干见午，壬干见酉，癸干见亥
        mapping = {
            Gan.JIA: Zhi.SI,    # 甲干见巳
            Gan.YI: Zhi.WU,     # 乙干见午
            Gan.BING: Zhi.ZI,   # 丙干见子
            Gan.DING: Zhi.SI,   # 丁干见巳
            Gan.WU: Zhi.WU,     # 戊干见午
            Gan.JI: Zhi.SHEN,   # 己干见申
            Gan.GENG: Zhi.YIN,  # 庚干见寅
            Gan.XIN: Zhi.WU,    # 辛干见午
            Gan.REN: Zhi.YOU,   # 壬干见酉
            Gan.GUI: Zhi.HAI    # 癸干见亥
        }
        # 在流年大运查询中，应该用原盘的年干或日干来查询
        # 检查年干
        if chart.year_gan._gan in mapping and zhi_in == mapping[chart.year_gan._gan]:
            return True
        # 检查日干
        if chart.day_gan._gan in mapping and zhi_in == mapping[chart.day_gan._gan]:
            return True
        return False

class Jinyu(Shensha):
    def __init__(self):
        super().__init__(source='day_gan', shensha_type='贵人')
        self.impact = {
            'career': 1,
            'love': 0,
            'study': 0,
            'health': 0,
            'life': 1,
            'spirituality': 0,
            'interpersonal': 0,
            'overall': 0,
        }
    @property
    def chinese_name(self):
        return "金舆"
    def is_present(self, chart):
        mapping = {
            Gan.JIA: Zhi.CHEN, Gan.YI: Zhi.SI, Gan.BING: Zhi.WEI, Gan.DING: Zhi.SHEN,
            Gan.WU: Zhi.WEI, Gan.JI: Zhi.SHEN, Gan.GENG: Zhi.XU, Gan.XIN: Zhi.HAI,
            Gan.REN: Zhi.CHOU, Gan.GUI: Zhi.YIN
        }
        positions = []
        for gan, zhi in mapping.items():
            if chart.day_gan._gan == gan and zhi in [z._zhi for z in chart.zhi_list]:
                for zhu in chart.zhu_list:
                    if zhu.zhi._zhi == zhi:
                        positions.append(zhu)
        word = f"金舆：{','.join([zhu.chinese_name for zhu in positions])}" if positions else "无金舆"
        return positions, word
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        mapping = {
            Gan.JIA: Zhi.CHEN, Gan.YI: Zhi.SI, Gan.BING: Zhi.WEI, Gan.DING: Zhi.SHEN,
            Gan.WU: Zhi.WEI, Gan.JI: Zhi.SHEN, Gan.GENG: Zhi.XU, Gan.XIN: Zhi.HAI,
            Gan.REN: Zhi.CHOU, Gan.GUI: Zhi.YIN
        }
        return any((gan_in == gan and zhi_in == zhi) for gan, zhi in mapping.items())

class Zaisha(Shensha):
    def __init__(self):
        super().__init__(source='year_zhi', shensha_type='煞')
        self.impact = {
            'career': -2,
            'love': -1,
            'study': -1,
            'health': -3,
            'life': -2,
            'spirituality': 0,
            'interpersonal': -1,
            'overall': -2,
        }
    @property
    def chinese_name(self):
        return "灾煞"
    def is_present(self, chart):
        # 灾煞查法：以年支为主，四柱地支中，与年支三合局的"墓"支相冲的那个地支
        # 申子辰（三合水局）见午，亥卯未（三合木局）见酉，寅午戌（三合火局）见子，巳酉丑（三合金局）见卯
        zaisha_map = {
            Zhi.SHEN: Zhi.WU, Zhi.ZI: Zhi.WU, Zhi.CHEN: Zhi.WU,  # 申子辰见午
            Zhi.HAI: Zhi.YOU, Zhi.MAO: Zhi.YOU, Zhi.WEI: Zhi.YOU,  # 亥卯未见酉
            Zhi.YIN: Zhi.ZI, Zhi.WU: Zhi.ZI, Zhi.XU: Zhi.ZI,  # 寅午戌见子
            Zhi.SI: Zhi.MAO, Zhi.YOU: Zhi.MAO, Zhi.CHOU: Zhi.MAO  # 巳酉丑见卯
        }
        positions = []
        year_zhi = chart.year_zhi._zhi
        if year_zhi in zaisha_map:
            zaisha_zhi = zaisha_map[year_zhi]
            for i, zhi in enumerate(chart.zhi_list):
                if zhi._zhi == zaisha_zhi:
                    positions.append(chart.zhu_list[i])
        word = f"年支{chart.year_zhi._zhi.chinese_name}见{zaisha_map[chart.year_zhi._zhi].chinese_name}为灾煞" if positions else "无灾煞"
        return positions, word
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        zaisha_map = {
            Zhi.SHEN: Zhi.WU, Zhi.ZI: Zhi.WU, Zhi.CHEN: Zhi.WU,
            Zhi.HAI: Zhi.YOU, Zhi.MAO: Zhi.YOU, Zhi.WEI: Zhi.YOU,
            Zhi.YIN: Zhi.ZI, Zhi.WU: Zhi.ZI, Zhi.XU: Zhi.ZI,
            Zhi.SI: Zhi.MAO, Zhi.YOU: Zhi.MAO, Zhi.CHOU: Zhi.MAO
        }
        year_zhi = chart.year_zhi._zhi
        if year_zhi in zaisha_map:
            return zhi_in == zaisha_map[year_zhi]
        return False

class Bazhuan(Shensha):
    def __init__(self):
        super().__init__(source='day_zhu', shensha_type='煞')
        self.impact = {
            'career': -1,
            'love': -1,
            'study': 0,
            'health': -1,
            'life': -1,
            'spirituality': 0,
            'interpersonal': -1,
            'overall': -1,
        }
    @property
    def chinese_name(self):
        return "八专"
    def is_present(self, chart):
        bazhuan_list = [(Gan.JIA, Zhi.YIN), (Gan.YI, Zhi.MAO), (Gan.WU, Zhi.WEI), (Gan.JI, Zhi.WEI), (Gan.GENG, Zhi.SHEN), (Gan.XIN, Zhi.YOU), (Gan.WU, Zhi.XU), (Gan.GUI, Zhi.CHOU)]
        positions = []
        if (chart.day_gan._gan, chart.day_zhi._zhi) in bazhuan_list:
            positions.append(chart.day_zhu)
        word = f"八专：{','.join([str(z) for z in positions])}" if positions else "无八专"
        return positions, word
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        # 八专日只与原盘日柱有关，流年大运中不可能出现
        return False

class Tongzi(Shensha):
    def __init__(self):
        super().__init__(source='day_zhi_or_hour_zhi', shensha_type='煞')
        self.impact = {
            'career': 0,
            'love': -1,
            'study': 0,
            'health': -1,
            'life': 0,
            'spirituality': 2,
            'interpersonal': 0,
            'overall': 0,
        }
    @property
    def chinese_name(self):
        return "童子"
    def is_present(self, chart):
        """
        童子查法：
        1. 春秋寅子贵：春季（寅卯辰月）或秋季（申酉戌月）生，日支或时支见寅或子。
        2. 冬夏卯未辰：冬季（亥子丑月）或夏季（巳午未月）生，日支或时支见卯、未、辰。
        3. 金木马卯合：年柱纳音为金或木，日支或时支见午或卯。
        4. 水火鸡犬多：年柱纳音为水或火，日支或时支见酉或戌。
        5. 土命逢辰巳：年柱纳音为土，日支或时支见辰或巳。
        归属原则：只在实际命中童子条件的日支或时支所在柱append，不能因为日支或时支在总list里就都加。
        """
        found = []
        reasons = []
        positions = []
        # 月支判断季节
        spring = [Zhi.YIN, Zhi.MAO, Zhi.CHEN]
        summer = [Zhi.SI, Zhi.WU, Zhi.WEI]
        autumn = [Zhi.SHEN, Zhi.YOU, Zhi.XU]
        winter = [Zhi.HAI, Zhi.ZI, Zhi.CHOU]
        nayin_jin = ["海中金", "剑锋金", "白蜡金", "沙中金", "金箔金", "钗钏金"]
        nayin_mu = ["大林木", "杨柳木", "松柏木", "平地木", "桑柘木", "石榴木"]
        nayin_shui = ["涧下水", "泉中水", "长流水", "天河水", "大溪水", "大海水"]
        nayin_huo = ["炉中火", "山头火", "霹雳火", "山下火", "覆灯火", "天上火"]
        nayin_tu = ["屋上土", "城头土", "壁上土", "大驿土", "沙中土", "路旁土"]
        # 记录每条规则命中的柱
        # 1. 春秋寅子贵
        if chart.month_zhi._zhi in spring + autumn:
            for idx, zhu in enumerate([chart.day_zhu, getattr(chart, 'hour_zhu', None)]):
                if zhu and [chart.day_zhi._zhi, getattr(chart, 'hour_zhi', None) and chart.hour_zhi._zhi][idx] in [Zhi.YIN, Zhi.ZI]:
                    positions.append(zhu)
                    found.append("春秋寅子贵")
                    reasons.append(f"{chart.month_zhi._zhi.chinese_name}月，{['日支','时支'][idx]}见寅/子")
        # 2. 冬夏卯未辰
        if chart.month_zhi._zhi in winter + summer:
            for idx, zhu in enumerate([chart.day_zhu, getattr(chart, 'hour_zhu', None)]):
                if zhu and [chart.day_zhi._zhi, getattr(chart, 'hour_zhi', None) and chart.hour_zhi._zhi][idx] in [Zhi.MAO, Zhi.WEI, Zhi.CHEN]:
                    positions.append(zhu)
                    found.append("冬夏卯未辰")
                    reasons.append(f"{chart.month_zhi._zhi.chinese_name}月，{['日支','时支'][idx]}见卯/未/辰")
        # 3. 金木马卯合
        nayin = getattr(chart, 'year_nayin', None)
        if nayin in nayin_jin + nayin_mu:
            for idx, zhu in enumerate([chart.day_zhu, getattr(chart, 'hour_zhu', None)]):
                if zhu and [chart.day_zhi._zhi, getattr(chart, 'hour_zhi', None) and chart.hour_zhi._zhi][idx] in [Zhi.WU, Zhi.MAO]:
                    positions.append(zhu)
                    found.append("金木马卯合")
                    reasons.append(f"年纳音{nayin}，{['日支','时支'][idx]}见午/卯")
        # 4. 水火鸡犬多
        if nayin in nayin_shui + nayin_huo:
            for idx, zhu in enumerate([chart.day_zhu, getattr(chart, 'hour_zhu', None)]):
                if zhu and [chart.day_zhi._zhi, getattr(chart, 'hour_zhi', None) and chart.hour_zhi._zhi][idx] in [Zhi.YOU, Zhi.XU]:
                    positions.append(zhu)
                    found.append("水火鸡犬多")
                    reasons.append(f"年纳音{nayin}，{['日支','时支'][idx]}见酉/戌")
        # 5. 土命逢辰巳
        if nayin in nayin_tu:
            for idx, zhu in enumerate([chart.day_zhu, getattr(chart, 'hour_zhu', None)]):
                if zhu and [chart.day_zhi._zhi, getattr(chart, 'hour_zhi', None) and chart.hour_zhi._zhi][idx] in [Zhi.CHEN, Zhi.SI]:
                    positions.append(zhu)
                    found.append("土命逢辰巳")
                    reasons.append(f"年纳音{nayin}，{['日支','时支'][idx]}见辰/巳")
        # 去重
        positions = list(dict.fromkeys(positions))
        word = f"童子：{'，'.join(found)}" if found else "无童子"
        if reasons:
            word += "（" + "；".join(reasons) + "）"
        return positions, word

    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        # 只要该柱支命中上述任一条即可
        # 只查日支和时支
        zhi_list = [chart.day_zhi._zhi]
        if hasattr(chart, 'hour_zhi') and chart.hour_zhi:
            zhi_list.append(chart.hour_zhi._zhi)
        if zhi_in not in zhi_list:
            return False
        # 月支判断季节
        spring = [Zhi.YIN, Zhi.MAO, Zhi.CHEN]
        summer = [Zhi.SI, Zhi.WU, Zhi.WEI]
        autumn = [Zhi.SHEN, Zhi.YOU, Zhi.XU]
        winter = [Zhi.HAI, Zhi.ZI, Zhi.CHOU]
        nayin = getattr(chart, 'year_nayin', None)
        nayin_jin = ["海中金", "剑锋金", "白蜡金", "沙中金", "金箔金", "钗钏金"]
        nayin_mu = ["大林木", "杨柳木", "松柏木", "平地木", "桑柘木", "石榴木"]
        nayin_shui = ["涧下水", "泉中水", "长流水", "天河水", "大溪水", "大海水"]
        nayin_huo = ["炉中火", "山头火", "霹雳火", "山下火", "覆灯火", "天上火"]
        nayin_tu = ["屋上土", "城头土", "壁上土", "大驿土", "沙中土", "路旁土"]
        # 1
        if chart.month_zhi._zhi in spring + autumn and zhi_in in [Zhi.YIN, Zhi.ZI]:
            return True
        # 2
        if chart.month_zhi._zhi in winter + summer and zhi_in in [Zhi.MAO, Zhi.WEI, Zhi.CHEN]:
            return True
        # 3
        if nayin in nayin_jin + nayin_mu and zhi_in in [Zhi.WU, Zhi.MAO]:
            return True
        # 4
        if nayin in nayin_shui + nayin_huo and zhi_in in [Zhi.YOU, Zhi.XU]:
            return True
        # 5
        if nayin in nayin_tu and zhi_in in [Zhi.CHEN, Zhi.SI]:
            return True
        return False

class Yinchayancuo(Shensha):
    def __init__(self):
        super().__init__(source='day_zhu', shensha_type='煞')
        self.impact = {
            'career': 0,
            'love': -2,
            'study': 0,
            'health': 0,
            'life': 0,
            'spirituality': 0,
            'interpersonal': -1,
            'overall': 0
        }
    @property
    def chinese_name(self):
        return "阴差阳错"
    def is_present(self, chart):
        yincha_days = [
            (Gan.BING, Zhi.ZI), (Gan.DING, Zhi.CHOU), (Gan.WU, Zhi.YIN), (Gan.XIN, Zhi.MAO),
            (Gan.REN, Zhi.CHEN), (Gan.GUI, Zhi.SI), (Gan.BING, Zhi.WU), (Gan.DING, Zhi.WEI),
            (Gan.WU, Zhi.SHEN), (Gan.XIN, Zhi.YOU), (Gan.REN, Zhi.XU), (Gan.GUI, Zhi.HAI)
        ]
        if (chart.day_gan._gan, chart.day_zhi._zhi) in yincha_days:
            return [chart.day_zhu], f"日柱{chart.day_gan._gan.chinese_name}{chart.day_zhi._zhi.chinese_name}为阴差阳错日"
        return [], "无阴差阳错"
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        # 阴差阳错只与原盘日柱有关，流年大运中不可能出现
        return False

class ShieDabai(Shensha):
    def __init__(self):
        super().__init__(source='day_zhu', shensha_type='煞')
        self.impact = {
            'career': -2,
            'love': 0,
            'study': 0,
            'health': -1,
            'life': -2,
            'spirituality': 0,
            'interpersonal': -1,
            'overall': -1
        }
    @property
    def chinese_name(self):
        return "十恶大败"
    def is_present(self, chart):
        dabai_days = [
            (Gan.JIA, Zhi.CHEN), (Gan.YI, Zhi.SI), (Gan.BING, Zhi.SHEN), (Gan.DING, Zhi.HAI),
            (Gan.WU, Zhi.XU), (Gan.JI, Zhi.CHOU), (Gan.GENG, Zhi.CHEN), (Gan.XIN, Zhi.SI),
            (Gan.REN, Zhi.SHEN), (Gan.GUI, Zhi.HAI)
        ]
        if (chart.day_gan._gan, chart.day_zhi._zhi) in dabai_days:
            return [chart.day_zhu], f"日柱{chart.day_gan._gan.chinese_name}{chart.day_zhi._zhi.chinese_name}为十恶大败日"
        return [], "无十恶大败"
    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        # 十恶大败只与原盘日柱有关，流年大运中不可能出现
        return False

class Tianyii(Shensha):
    def __init__(self):
        super().__init__(source='month_zhi', shensha_type='贵人')
        self.impact = {
            'career': 0,
            'love': 0,
            'study': 0,
            'health': 3,
            'life': 1,
            'spirituality': 0,
            'interpersonal': 0,
            'overall': 0
        }

    @property
    def chinese_name(self):
        return "天医贵人"

    def is_present(self, chart):
        """
        天医贵人查法：
        正月生人见丑；二月生人见寅，三月生人见卯，四月生人见辰、五月生人见巳、六月生人见午；
        七月生人见未，八月生人见申、九月生人见酉、十月生人见戌，十一月生人见亥，十二月生人见子。
        以月支为主，查四柱地支中有否。
        """
        tianyi_map = {
            Zhi.YIN: [Zhi.CHOU],      # 正月（寅）见丑
            Zhi.MAO: [Zhi.YIN],      # 二月（卯）见寅
            Zhi.CHEN: [Zhi.MAO],     # 三月（辰）见卯
            Zhi.SI: [Zhi.CHEN],      # 四月（巳）见辰
            Zhi.WU: [Zhi.SI],        # 五月（午）见巳
            Zhi.WEI: [Zhi.WU],       # 六月（未）见午
            Zhi.SHEN: [Zhi.WEI],     # 七月（申）见未
            Zhi.YOU: [Zhi.SHEN],     # 八月（酉）见申
            Zhi.XU: [Zhi.YOU],       # 九月（戌）见酉
            Zhi.HAI: [Zhi.XU],       # 十月（亥）见戌
            Zhi.ZI: [Zhi.HAI],       # 十一月（子）见亥
            Zhi.CHOU: [Zhi.ZI]       # 十二月（丑）见子
        }
        found = []
        month_zhi = chart.month_zhi._zhi
        if month_zhi in tianyi_map:
            tianyi_zhi = tianyi_map[month_zhi]
            for zhu in chart.zhu_list:
                if zhu.zhi._zhi in tianyi_zhi:
                    found.append(zhu)
        if found:
            word = f"天医贵人：{','.join([z.chinese_name for z in found])}"
        else:
            word = "无天医贵人"
        return found, word

    def is_present_in_zhu(self, gan_in, zhi_in, chart):
        tianyi_map = {
            Zhi.YIN: [Zhi.CHOU],
            Zhi.MAO: [Zhi.YIN],
            Zhi.CHEN: [Zhi.MAO],
            Zhi.SI: [Zhi.CHEN],
            Zhi.WU: [Zhi.SI],
            Zhi.WEI: [Zhi.WU],
            Zhi.SHEN: [Zhi.WEI],
            Zhi.YOU: [Zhi.SHEN],
            Zhi.XU: [Zhi.YOU],
            Zhi.HAI: [Zhi.XU],
            Zhi.ZI: [Zhi.HAI],
            Zhi.CHOU: [Zhi.ZI],
        }
        month_zhi = chart.month_zhi._zhi
        if month_zhi in tianyi_map:
            return zhi_in in tianyi_map[month_zhi]
        return False