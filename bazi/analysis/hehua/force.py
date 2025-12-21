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

# analysis/hehua/force.py

class Force:
    def __init__(self, cate, elements, element_index, E):
        self.cate = cate
        self.elements = elements
        self.element_index = element_index
        self.E = E
        self.field = self.get_field()
        self.item_list = [self.elements[i]._chinese_name + self.elements[i]._wuxing.chinese_name for i in range(len(self.elements))]
        idx_name_list = ["年", "月", "日", "时"]
        self.idx_list = [f"{idx_name_list[i]}" for i in self.element_index]  # 简化

    def get_field(self):
        raise NotImplementedError

    def get_log(self):
        raise NotImplementedError
    
    def get_cate(self):
        return self.cate


class TianGanHe(Force):
    def __init__(self, elements, element_index, wuxing, is_hua, E):
        super().__init__('天干相合', elements, element_index, E)
        self.wuxing = wuxing
        self.is_hua = is_hua

    def get_field(self):
        return "天干"
    
    def get_log(self):
        tiangan_index_and_name_list = [self.idx_list[i] + self.get_field()[-1] + self.item_list[i] for i in range(2)]
        log = f"{'与'.join(tiangan_index_and_name_list)}相合，{'合化' + self.wuxing.chinese_name + '成功' if self.is_hua else '合而不化'}"
        return log


class TianGanChong(Force):
    def __init__(self, elements, element_index, distance, E):
        super().__init__('天干相冲', elements, element_index, E)
        self.distance = distance

    def get_field(self):
        return "天干"

    def get_log(self):
        tiangan_index_and_name_list = [self.idx_list[i] + self.get_field()[-1] + self.item_list[i] for i in range(2)]
        log = f"{'与'.join(tiangan_index_and_name_list)}相冲"
        return log


class DiZhiSanHui(Force):
    def __init__(self, elements, element_index, wuxing, E):
        super().__init__('地支三会', elements, element_index, E)
        self.wuxing = wuxing

    def get_field(self):
        return "地支"

    def get_log(self):
        dizhi_index_and_name_list = [self.idx_list[i] + self.get_field()[-1] + self.item_list[i] for i in range(3)]
        log = f"{'与'.join(dizhi_index_and_name_list)}三会{self.wuxing.chinese_name}"
        return log


class DiZhiSanHe(Force):
    def __init__(self, elements, element_index, wuxing, E):
        super().__init__('地支三合', elements, element_index, E)
        self.wuxing = wuxing

    def get_field(self):
        return "地支"

    def get_log(self):
        dizhi_index_and_name_list = [self.idx_list[i] + self.get_field()[-1] + self.item_list[i] for i in range(3)]
        log = f"{'与'.join(dizhi_index_and_name_list)}三合{self.wuxing.chinese_name}"
        return log


class DiZhiBanHe(Force):
    def __init__(self, elements, element_index, wuxing, distance, E):
        super().__init__('地支半合', elements, element_index, E)
        self.wuxing = wuxing
        self.distance = distance

    def get_field(self):
        return "地支"

    def get_log(self):
        dizhi_index_and_name_list = [self.idx_list[i] + self.get_field()[-1] + self.item_list[i] for i in range(2)]
        log = f"{'与'.join(dizhi_index_and_name_list)}半合{self.wuxing.chinese_name}"
        return log


class DiZhiLiuHe(Force):
    def __init__(self, elements, element_index, wuxing, is_hua, E):
        super().__init__('地支六合', elements, element_index, E)
        self.wuxing = wuxing
        self.is_hua = is_hua

    def get_field(self):
        return "地支"

    def get_log(self):
        dizhi_index_and_name_list = [self.idx_list[i] + self.get_field()[-1] + self.item_list[i] for i in range(2)]
        log = f"{'与'.join(dizhi_index_and_name_list)}六合，{'合化' + self.wuxing.chinese_name + '成功' if self.is_hua else '合而不化'}"
        return log


class DiZhiLiuChong(Force):
    def __init__(self, elements, element_index, distance, E):
        super().__init__('地支六冲', elements, element_index, E)
        self.distance = distance

    def get_field(self):
        return "地支"

    def get_log(self):
        dizhi_index_and_name_list = [self.idx_list[i] + self.get_field()[-1] + self.item_list[i] for i in range(2)]
        log = f"{'与'.join(dizhi_index_and_name_list)}六冲"
        return log
