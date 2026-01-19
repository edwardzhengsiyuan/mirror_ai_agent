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

# analysis/power/bazi_power_chart.py
import copy

from ...core import Shishen, Wuxing, Gan, ShenQiangRuo

# 定义全局变量
MRateList = [
    [1],          # 当地支藏干只有一个时
    [0.7, 0.3],   # 当地支藏干有两个时
    [0.5, 0.3, 0.2]  # 当地支藏干有三个时
]

MInitial = 1  # 初始M值

class BaziPowerChartElement:
    def __init__(self, gan, x, y, M=MInitial, shishen=Shishen.RIZHU):
        self.gan = gan
        self.x = x
        self.y = y
        self.M = M
        self.shishen = shishen
        self.wuxing_power = self.initialize_wuxing_power()

    def initialize_wuxing_power(self):
        wuxing_power = {Wuxing.MU: 0, Wuxing.HUO: 0, Wuxing.TU: 0, Wuxing.JIN: 0, Wuxing.SHUI: 0}
        wuxing_power[self.gan.wuxing] = 1
        return wuxing_power

    def __repr__(self):
        return f"BaziPowerChartElement(Name={self.gan.name}, Wuxing={self.gan.wuxing.name}, M={self.M}, Shishen={self.shishen.name}, x={self.x}, y={self.y}, WuxingPower={self.wuxing_power})"

class BaziPowerChart:
    def __init__(self, bazi_chart, force):
        self.bazi_chart = bazi_chart
        self.fixed_row = self.initialize_fixed_row()
        self.variable_row = self.initialize_variable_row()
        self.shishen_power = {shishen: 0 for shishen in Shishen}
        self.gan_power = {gan: 0 for gan in Gan}
        self.gan_proportions = {gan: 0 for gan in Gan}
        self.wuxing_power = {wuxing: 0 for wuxing in Wuxing}
        self.wuxing_proportions = {wuxing: 0 for wuxing in Wuxing}
        self.rizhu_strength = 0
        self.force = force
        self.shenqiangruo: ShenQiangRuo | None = None

        # 在初始化中不计算五行和十神的力量
        # 等待 PowerTransformer 执行完毕后，再调用计算方法

    def initialize_fixed_row(self):
        fixed_row = []
        for index, gan in enumerate(self.bazi_chart._gan_list):
            fixed_row.append(BaziPowerChartElement(gan._gan, x=index, y=0, M=MInitial, shishen=gan._shishen))
        return fixed_row

    def initialize_variable_row(self):
        variable_row = []
        for index, zhi in enumerate(self.bazi_chart._zhi_list):
            row = []
            hidden_gans = zhi._hidden_gans
            shishen_list = zhi._hidden_gans_shishen_list
            num_elements = len(hidden_gans)
            M_values = MRateList[num_elements - 1] if num_elements > 0 else []
            for i, (gan, shishen) in enumerate(zip(hidden_gans, shishen_list)):
                M = M_values[i]
                row.append(BaziPowerChartElement(gan, x=index, y=1, M=M, shishen=shishen))
            variable_row.append(row)
        return variable_row

    def calculate_powers(self):
        # 在 transformations 完成后，调用此方法计算五行和十神的力量
        self.calculate_shishen()
        self.calculate_wuxing_proportions()
        self.calculate_shishen_proportions()
        self.rizhu_strength = self.evaluate_rizhu_strength()
        self.calculate_gan_power()

    def calculate_shishen(self):
        self.shishen_power = {shishen: 0 for shishen in Shishen}
        for element in self.fixed_row + [item for sublist in self.variable_row for item in sublist]:
            self.shishen_power[element.shishen] += element.wuxing_power[element.gan.wuxing] * element.M
        # self.translate_shishen()

    def translate_shishen(self):
        # 只移除日主，不再做七杀/偏印的转换
        self.shishen_power.pop(Shishen.RIZHU, None)

    def calculate_wuxing_proportions(self):
        wuxing_totals = {wuxing: 0 for wuxing in Wuxing}
        total_power = 0

        # 计算天干的五行力量
        for element in self.fixed_row:
            for wuxing, power in element.wuxing_power.items():
                wuxing_totals[wuxing] += power * element.M
                total_power += power * element.M

        # 计算地支的五行力量
        for sublist in self.variable_row:
            for element in sublist:
                for wuxing, power in element.wuxing_power.items():
                    wuxing_totals[wuxing] += power * element.M
                    total_power += power * element.M

        self.wuxing_power = wuxing_totals
        self.wuxing_proportions = {wuxing: total / total_power for wuxing, total in wuxing_totals.items()} if total_power > 0 else {wuxing: 0 for wuxing in Wuxing}

    def calculate_shishen_proportions(self):
        total_power = sum(self.shishen_power.values())
        self.shishen_proportions = {shishen: self.shishen_power[shishen] / total_power for shishen in self.shishen_power.keys()} if total_power > 0 else {shishen: 0 for shishen in Shishen}

    def evaluate_rizhu_strength(self):
        rizhu_wuxing = self.bazi_chart.day_gan._wuxing
        wuxing_totals = copy.deepcopy(self.wuxing_power)
        rizhu_element = self.fixed_row[2]  # 日干位于 fixed_row 的第三个元素（索引为 2）

        # Exclude Rizhu's own power
        for wuxing, power in rizhu_element.wuxing_power.items():
            wuxing_totals[wuxing] -= power * rizhu_element.M

        # Calculate supporting and opposing forces
        supporting_power = (wuxing_totals.get(rizhu_wuxing, 0) +
                            wuxing_totals.get(Wuxing((rizhu_wuxing.value + 4) % 5), 0) * 0.8)
        opposing_power = (wuxing_totals.get(Wuxing((rizhu_wuxing.value + 3) % 5), 0) * 0.75 +
                          wuxing_totals.get(Wuxing((rizhu_wuxing.value + 2) % 5), 0) * 0.6 +
                          wuxing_totals.get(Wuxing((rizhu_wuxing.value + 1) % 5), 0) * 0.45)

        # Strength is the difference between supporting and opposing forces
        F = supporting_power - opposing_power
        return F

    def calculate_gan_power(self):
        total_power = 0

        # 计算每个天干的力量
        for element in self.fixed_row:
            power = element.wuxing_power[element.gan.wuxing] * element.M
            self.gan_power[element.gan] += power
            total_power += power

        for sublist in self.variable_row:
            for element in sublist:
                power = element.wuxing_power[element.gan.wuxing] * element.M
                self.gan_power[element.gan] += power
                total_power += power

        # 计算比例
        if total_power > 0:
            for gan, power in self.gan_power.items():
                self.gan_proportions[gan] = power / total_power
        else:
            self.gan_proportions = {gan: 0 for gan in Gan}

    def get_gan_power(self):
        return self.gan_power

    def get_gan_proportions(self):
        return self.gan_proportions

    def get_element(self, field, index):
        if field == "天干":
            return self.fixed_row[index]
        elif field == "地支":
            return self.variable_row[index]
        else:
            raise ValueError("Invalid field type")
