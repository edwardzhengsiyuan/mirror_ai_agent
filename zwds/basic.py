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

    @classmethod
    def from_chinese(cls, name):
        chinese_names = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        return cls(chinese_names.index(name))


year2month = {
    "甲": ['丙寅', '丁卯', '戊辰', '己巳', '庚午', '辛未', '壬申', '癸酉', '甲戌', '乙亥', '丙子', '丁丑'],
    "乙": ['戊寅', '己卯', '庚辰', '辛巳', '壬午', '癸未', '甲申', '乙酉', '丙戌', '丁亥', '戊子', '己丑'],
    "丙": ['庚寅', '辛卯', '壬辰', '癸巳', '甲午', '乙未', '丙申', '丁酉', '戊戌', '己亥', '庚子', '辛丑'],
    "丁": ['壬寅', '癸卯', '甲辰', '乙巳', '丙午', '丁未', '戊申', '己酉', '庚戌', '辛亥', '壬子', '癸丑'],
    "戊": ['甲寅', '乙卯', '丙辰', '丁巳', '戊午', '己未', '庚申', '辛酉', '壬戌', '癸亥', '甲子', '乙丑'],
    "己": ['丙寅', '丁卯', '戊辰', '己巳', '庚午', '辛未', '壬申', '癸酉', '甲戌', '乙亥', '丙子', '丁丑'],
    "庚": ['戊寅', '己卯', '庚辰', '辛巳', '壬午', '癸未', '甲申', '乙酉', '丙戌', '丁亥', '戊子', '己丑'],
    "辛": ['庚寅', '辛卯', '壬辰', '癸巳', '甲午', '乙未', '丙申', '丁酉', '戊戌', '己亥', '庚子', '辛丑'],
    "壬": ['壬寅', '癸卯', '甲辰', '乙巳', '丙午', '丁未', '戊申', '己酉', '庚戌', '辛亥', '壬子', '癸丑'],
    "癸": ['甲寅', '乙卯', '丙辰', '丁巳', '戊午', '己未', '庚申', '辛酉', '壬戌', '癸亥', '甲子', '乙丑'],
}

# 五行局对照表（按表格结构排列）
wuxing_ju_table = {
    '甲': ['水二局', '火六局', '木三局', '土五局', '金四局', '火六局'],
    '乙': ['火六局', '土五局', '金四局', '木三局', '水二局', '土五局'],
    '丙': ['土五局', '木三局', '水二局', '金四局', '火六局', '木三局'],
    '丁': ['木三局', '金四局', '火六局', '水二局', '土五局', '金四局'],
    '戊': ['金四局', '水二局', '土五局', '火六局', '木三局', '水二局'],
    '己': ['水二局', '火六局', '木三局', '土五局', '金四局', '火六局'],
    '庚': ['火六局', '土五局', '金四局', '木三局', '水二局', '土五局'],
    '辛': ['土五局', '木三局', '水二局', '金四局', '火六局', '木三局'],
    '壬': ['木三局', '金四局', '火六局', '水二局', '土五局', '金四局'],
    '癸': ['金四局', '水二局', '土五局', '火六局', '木三局', '水二局']
}

JU_NUM_MAP = {
    '水二局': 2,
    '木三局': 3,
    '金四局': 4,
    '土五局': 5,
    '火六局': 6
}

ziwei_table = {
    2: [  # 水二局
        '丑','寅','寅','卯','卯','辰','辰','巳','巳','午','午','未','未','申','申',  # 1-15日
        '酉','酉','戌','戌','亥','亥','子','子','丑','丑','寅','寅','卯','卯','辰'   # 16-30日
    ],
    3: [  # 木三局
        '辰','丑','寅','巳','寅','卯','午','卯','辰','未','辰','巳','申','巳','午',  # 1-15
        '酉','午','未','戌','未','申','亥','申','酉','子','酉','戌','丑','戌','亥'   # 16-30
    ],
    4: [  # 金四局
        '亥','辰','丑','寅','子','巳','寅','卯','丑','午','卯','辰','寅','未','辰',  # 1-15
        '巳','卯','申','巳','午','辰','酉','午','未','巳','戌','未','申','午','亥'   # 16-30
    ],
    5: [  # 土五局（修正第28日"西"为"酉"）
        '午','亥','辰','丑','寅','未','子','巳','寅','卯','申','丑','午','卯','辰',  # 1-15
        '酉','寅','未','辰','巳','戌','卯','申','巳','午','亥','辰','酉','午','未'   # 16-30
    ],
    6: [  # 火六局
        '酉','午','亥','辰','丑','寅','戌','未','子','巳','寅','卯','亥','申','丑',  # 1-15
        '午','卯','辰','子','酉','寅','未','辰','巳','丑','戌','卯','申','巳','午'   # 16-30
    ]
}

ziwei_star_map = {
    '紫微': ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'],
    '天机': ['亥', '子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌'],
    '太阳': ['酉', '戌', '亥', '子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申'],
    '武曲': ['申', '酉', '戌', '亥', '子', '丑', '寅', '卯', '辰', '巳', '午', '未'],
    '天同': ['未', '申', '酉', '戌', '亥', '子', '丑', '寅', '卯', '辰', '巳', '午'], 
    '廉贞': ['辰', '巳', '午', '未', '申', '酉', '戌', '亥', '子', '丑', '寅', '卯'],
    '天府': ['辰', '卯', '寅', '丑', '子', '亥', '戌', '酉', '申', '未', '午', '巳'],
    '太阴': ['巳', '辰', '卯', '寅', '丑', '子', '亥', '戌', '酉', '申', '未', '午'],
    '贪狼': ['午', '巳', '辰', '卯', '寅', '丑', '子', '亥', '戌', '酉', '申', '未'],
    '巨门': ['未', '午', '巳', '辰', '卯', '寅', '丑', '子', '亥', '戌', '酉', '申'],
    '天相': ['申', '未', '午', '巳', '辰', '卯', '寅', '丑', '子', '亥', '戌', '酉'],
    '天梁': ['酉', '申', '未', '午', '巳', '辰', '卯', '寅', '丑', '子', '亥', '戌'],
    '七杀': ['戌', '酉', '申', '未', '午', '巳', '辰', '卯', '寅', '丑', '子', '亥'],
    '破军': ['寅', '丑', '子', '亥', '戌', '酉', '申', '未', '午', '巳', '辰', '卯']
}

# 固定时辰映射的星曜
time_fixed_stars = {
    '文昌': ['戌','酉','申','未','午','巳','辰','卯','寅','丑','子','亥'],
    '文曲': ['辰','巳','午','未','申','酉','戌','亥','子','丑','寅','卯'],
    '地劫': ['亥','子','丑','寅','卯','辰','巳','午','未','申','酉','戌'],
    '天空': ['亥','戌','酉','申','未','午','巳','辰','卯','寅','丑','子'],
    '台辅': ['午','未','申','酉','戌','亥','子','丑','寅','卯','辰','巳'],
    '封诰': ['寅','卯','辰','巳','午','未','申','酉','戌','亥','子','丑']
}

# 火星表（修正"西"为"酉"）
huoxing_table = {
    '火': ['丑','寅','卯','辰','巳','午','未','申','酉','戌','亥','子'],  # 寅午戌年
    '水': ['寅','卯','辰','巳','午','未','申','酉','戌','亥','子','丑'],  # 申子辰年
    '金': ['卯','辰','巳','午','未','申','酉','戌','亥','子','丑','寅'],  # 巳酉丑年
    '木': ['酉','戌','亥','子','丑','寅','卯','辰','巳','午','未','申']   # 亥卯未年
}

# 铃星表（修正"西"为"酉"）
lingxing_table = {
    '火': ['卯','辰','巳','午','未','申','酉','戌','亥','子','丑','寅'],  # 寅午戌年
    '水': ['戌','亥','子','丑','寅','卯','辰','巳','午','未','申','酉'],  # 申子辰年
    '金': ['戌','亥','子','丑','寅','卯','辰','巳','午','未','申','酉'],  # 巳酉丑年
    '木': ['戌','亥','子','丑','寅','卯','辰','巳','午','未','申','酉']   # 亥卯未年
}

# 三合局判断字典（年支 → 三合局）
sanhe_mapping = {
    '寅': '火', '午': '火', '戌': '火',  # 寅午戌火局
    '申': '水', '子': '水', '辰': '水',  # 申子辰水局
    '巳': '金', '酉': '金', '丑': '金',  # 巳酉丑金局
    '亥': '木', '卯': '木', '未': '木'   # 亥卯未木局
}

# 月系诸星对照表（修正天姚十月"戊"为"戌"）
month_stars = {
    '左辅': ['辰','巳','午','未','申','酉','戌','亥','子','丑','寅','卯'],
    '右弼': ['戌','酉','申','未','午','巳','辰','卯','寅','丑','子','亥'],
    '天刑': ['酉','戌','亥','子','丑','寅','卯','辰','巳','午','未','申'],
    '天姚': ['丑','寅','卯','辰','巳','午','未','申','酉','戌','亥','子'],  
    '解神': ['申','申','戌','戌','子','子','寅','寅','辰','辰','午','午'],
    '天巫': ['巳','申','寅','亥','巳','申','寅','亥','巳','申','寅','亥'],
    '天月': ['戌','巳','辰','寅','未','卯','亥','未','寅','午','戌','寅'],
    '阴煞': ['寅','子','戌','申','午','辰','寅','子','戌','申','午','辰']
}

# 干系诸星位置表
gan_position_stars = {
    '禄存': ['寅','卯','巳','午','巳','午','申','酉','亥','子'],
    '擎羊': ['卯','辰','午','未','午','未','酉','戌','子','丑'],
    '陀罗': ['丑','寅','辰','巳','辰','巳','未','申','戌','亥'],
    '天魁': ['丑','子','亥','亥','丑','子','丑','午','卯','卯'],
    '天钺': ['未','申','酉','酉','未','申','未','寅','巳','巳'],
    '天官': ['未','辰','巳','寅','卯','酉','亥','酉','戌','午'],
    '天福': ['酉','申','子','亥','卯','寅','午','巳','午','巳']
}

SI_HUA_KEY = ["禄", "权", "科", "忌"]

# 四化对照表
SI_HUA_MAP = {
    '禄': ['廉贞','天机','天同','太阴','贪狼','武曲','太阳','巨门','天梁','破军'],
    '权': ['破军','天梁','天机','天同','太阴','贪狼','武曲','太阳','紫微','巨门'],
    '科': ['武曲','紫微','文昌','天机','右弼','天梁','太阴','文曲','左辅','太阴'],
    '忌': ['太阳','太阴','廉贞','巨门','天机','文曲','天同','文昌','武曲','贪狼']
}

# 年支映射表
zhi_based_stars = {
    '地空': ['丑','寅','卯','辰','巳','午','未','申','酉','戌','亥','子'],
    '天哭': ['午','巳','辰','卯','寅','丑','子','亥','戌','酉','申','未'],
    '天虚': ['午','未','申','酉','戌','亥','子','丑','寅','卯','辰','巳'],
    '龙池': ['辰','巳','午','未','申','酉','戌','亥','子','丑','寅','卯'],
    '凤阁': ['戌','酉','申','未','午','巳','辰','卯','寅','丑','子','亥'],
    '红鸾': ['卯','寅','丑','子','亥','戌','酉','申','未','午','巳','辰'],
    '天喜': ['酉','申','未','午','巳','辰','卯','寅','丑','子','亥','戌'],
    '蜚廉': ['申','酉','戌','巳','午','未','寅','卯','辰','亥','子','丑'],
    '破碎': ['巳','丑','酉','巳','丑','酉','巳','丑','酉','巳','丑','酉'],
    '孤辰': ['寅','寅','巳','巳','巳','申','申','申','亥','亥','亥','寅'],
    '天马': ['寅','亥','申','巳','寅','亥','申','巳','寅','亥','申','巳'],
    '寡宿': ['戌','戌','丑','丑','丑','辰','辰','辰','未','未','未','戌']
}

gong_name_list = ["命宫", "兄弟宫", "夫妻宫", "子女宫", "财帛宫", "疾厄宫", "迁移宫", "交友宫", "官禄宫", "田宅宫", "福德宫", "父母宫"]

main_star_list = ['七杀', '破军', '廉贞', '贪狼', '紫微', '天府', '武曲', '天相', '太阳', '巨门', '天机', '太阴', '天梁', '天同']

class HUA(Enum):
    LU = 0
    QUAN = 1
    KE = 2
    JI = 3

    @property
    def chinese_name(self):
        chinese_names = ["禄", "权", "科", "忌"]
        return chinese_names[self.value]

    @classmethod
    def from_chinese(cls, name):
        chinese_names = ["禄", "权", "科", "忌"]
        return cls(chinese_names.index(name))
    
class Force:
    def __init__(self, hua, start, end):
        self.hua = hua
        self.start = start
        self.end = end

    def get_start_or_end_name(self, num):
        if num < 0:
            return "生年"
        else:
            return Zhi(num)

class Star:
    def __init__(self, name):
        self.name = name
        self.hua = []

    def set_gong(self, gong):
        self.gong = gong

    def set_hua(self, hua):
        self.hua.append(hua)

class Gong:
    def __init__(self, zhi):
        self.zhi = zhi
        self.star_list = []
        self.is_shengong = False
        self.shengnian_hua = []
        self.name = []
        self.hua = dict()
        self.init_hua()
        self.duigong_star_list = []
        self.duigong = None
        self.sanfanggong = []

    def init_hua(self):
        for i in range(12):
            self.hua[i] = []

    def set_name(self, name):
        self.name.append(name)
    
    def add_star(self, star):
        self.star_list.append(star)

    def set_shengong(self):
        self.is_shengong = True

    def set_gan(self, gan):
        self.gan = gan

    def get_star(self):
        return self.star_list

    def set_shengnian_hua(self, hua):
        self.shengnian_hua.append(hua)

    def set_daxian(self, daxian):
        self.daxian = daxian

    def calcu_gong_name(self, mingzhi_num):
        dis = (mingzhi_num - self.zhi.value) % 12
        return gong_name_list[dis]
    
    def set_duigong_star(self, duigong_star_list ):
        self.duigong_star_list  = duigong_star_list

class Chart:
    def __init__(self, lunar, gender):
        self.lunar = lunar
        self.year_num = self.lunar.getYear()
        self.year_gan = Gan.from_chinese(lunar.getYearGan())
        self.year_zhi = Zhi.from_chinese(lunar.getYearZhi())
        month = lunar.getMonth()
        if month < 0:
            month = 0 - month + 1
        self.month_num = month
        month_ganzhi = year2month[self.year_gan.chinese_name][month-1]
        self.month_gan = Gan.from_chinese(month_ganzhi[0])
        self.month_zhi = Zhi.from_chinese(month_ganzhi[1])
        self.day_gan = Gan.from_chinese(lunar.getDayGanExact2())
        self.day_zhi = Zhi.from_chinese(lunar.getDayZhiExact2())
        self.day_num = lunar.getDay()
        self.hour_gan = Gan.from_chinese(lunar.getTimeGan())
        self.hour_zhi = Zhi.from_chinese(lunar.getTimeZhi())
        self.gong_name_list = gong_name_list
        self.gender = gender

    def set_chart_benming(self):
        self.init_gong_list()
        self.setup_mingshengong()
        self.setup_12gong()
        self.set_shengong()
        self.set_gong_gan()
        self.get_wuxing_ju()
        self.set_ziwei_relative_star()
        self.set_time_stars()
        self.set_month_stars()
        self.set_gan_stars()
        # self.set_shengnina_hua()
        self.set_forward()
        self.set_boshi_12stars()
        self.set_zhi_stars()
        self.set_tianshang_tianshi()
        self.set_duigong_sanfanggong()
        self.set_konggong_star()
        self.set_daxian()
        self.check_hua_by_gan()
        self.check_hua_by_gong()
        self.check_zhuanlu_zhuanji()
        self.check_lujichengshuang()

    def init_gong_list(self):
        self.gong_list = []
        for i in range(12):
            self.gong_list.append(Gong(Zhi(i)))

    def get_gong_by_zhi(self, zhi):
        for gong in self.gong_list:
            if gong.zhi == zhi:
                return gong

    def setup_mingshengong(self):
        self.ming_zhi = Zhi((self.month_zhi.value - self.hour_zhi.value)%12)
        self.shen_zhi = Zhi((self.month_zhi.value + self.hour_zhi.value)%12)

    def setup_12gong(self):
        for i in range(12):
            gong = self.get_gong_by_zhi(Zhi((self.ming_zhi.value-i)%12))
            gong.set_name(self.gong_name_list[i])
    
    def set_shengong(self):
        gong = self.get_gong_by_zhi(Zhi((self.shen_zhi.value)%12))
        gong.set_shengong
    
    def set_gong_gan(self):
        for i in range(12):
            ganzhi = year2month[self.year_gan.chinese_name][i]
            gan = Gan.from_chinese(ganzhi[0])
            zhi = Zhi.from_chinese(ganzhi[1])
            gong = self.get_gong_by_zhi(zhi)
            gong.set_gan(gan)

    def get_wuxing_ju(self):
        self.ju_name = wuxing_ju_table[self.year_gan.chinese_name][self.ming_zhi.value//2]
        self.ju_num = JU_NUM_MAP[self.ju_name]

    def add_star2gong(self, star: Star, gong: Gong):
        gong.add_star(star)
        star.set_gong(gong)

    def set_ziwei_relative_star(self):
        """
        获取紫微星位置
        :param birth_day: 出生日期（1-30）
        :param ju_num: 五行局数（2-6）
        :return: 地支名称
        """
        if self.day_num < 1 or self.day_num > 30:
            raise ValueError("出生日期需在1-30范围内")
        
        if self.ju_num not in [2,3,4,5,6]:
            raise ValueError("五行局数需为2-6的整数")

        ziwei_zhi = Zhi.from_chinese(ziwei_table[self.ju_num][self.day_num-1])

        for star in ziwei_star_map:
            star_item = Star(star)
            zhi = Zhi.from_chinese(ziwei_star_map[star][ziwei_zhi.value])
            gong = self.get_gong_by_zhi(zhi)
            self.add_star2gong(star_item, gong)

    def set_time_stars(self):
        """
        获取时系诸星位置
        :param hour_zhi: 出生时辰地支（子-亥）
        :param year_zhi: 出生年支（用于确定三合局）
        :return: 时系星位置字典
        """
        
        # 获取三合局类型
        sanhe_ju = sanhe_mapping[self.year_zhi.chinese_name]
        
        # 计算各星位置
        result = {}
        
        # 处理固定星曜
        for star, positions in time_fixed_stars.items():
            star_item = Star(star)
            zhi = Zhi.from_chinese(positions[self.hour_zhi.value])
            gong = self.get_gong_by_zhi(zhi)
            self.add_star2gong(star_item, gong)
        
        # 处理火星
        huo_positions = huoxing_table[sanhe_ju]
        huo_item = Star('火星')
        huo_zhi = Zhi.from_chinese(huo_positions[self.hour_zhi.value])
        huo_gong = self.get_gong_by_zhi(huo_zhi)
        self.add_star2gong(huo_item, huo_gong)
        
        # 处理铃星
        ling_positions = lingxing_table[sanhe_ju]
        ling_item = Star('铃星')
        ling_zhi = Zhi.from_chinese(ling_positions[self.hour_zhi.value])
        ling_gong = self.get_gong_by_zhi(ling_zhi)
        self.add_star2gong(ling_item, ling_gong)
        
        return result

    def set_month_stars(self):
        for star, positions in month_stars.items():
            star_item = Star(star)
            zhi = Zhi.from_chinese(positions[self.month_num - 1])
            gong = self.get_gong_by_zhi(zhi)
            self.add_star2gong(star_item, gong)

    def set_gan_stars(self):
        """
        获取干系诸星配置
        :param year_gan: 年干（甲-癸）
        :return: 包含干系星位置和四化的字典
        """
        # 生成位置信息
        for star, positions in gan_position_stars.items():
            star_item = Star(star)
            zhi = Zhi.from_chinese(positions[self.year_gan.value])
            gong = self.get_gong_by_zhi(zhi)
            self.add_star2gong(star_item, gong)
            if star == "禄存":
                self.lucun_zhi = zhi
        
    def get_star_and_gong_by_star(self, star_name):
        for gong in self.gong_list:
            for star in gong.get_star():
                if star.name == star_name:
                    return star, gong

    # def set_shengnina_hua(self):
    #     self.year_hua = dict()
    #     for hua in SI_HUA_MAP:
    #         positions = SI_HUA_MAP[hua]
    #         hua_item = HUA.from_chinese(hua)
    #         star_name = positions[self.year_gan.value]
    #         star_item, gong = self.get_star_and_gong_by_star(star_name)
    #         star_item.set_hua(hua_item)
    #         gong.set_shengnian_hua(hua_item)
    #         self.year_hua[hua] = (gong.name, star_name)

    def set_forward(self):
        # 判断顺逆：阳男阴女顺行，其他逆行

        yin_yang = self.year_gan.yinyang

        if (yin_yang.value == 1 and self.gender == 'male') or (yin_yang.value == 0 and self.gender == 'female'):
            self.is_forward = 1
        else:
            self.is_forward = -1

    # ======================
    # 博士十二星处理逻辑
    # ======================
    def set_boshi_12stars(self):
        """
        获取博士十二星位置
        :param lucun_zhi: 禄存地支位置
        :param yin_yang: 生年阴阳（'阳'/'阴'）
        :param gender: 性别（'男'/'女'）
        :return: 博士十二星字典
        """
        stars_order = ['博士','力士','青龙','小耗','将军','奏书','蜚廉','喜神','病符','大耗','伏兵','官府']
        
        zhi = self.lucun_zhi
        for star in stars_order:
            star_item = Star(star)
            gong = self.get_gong_by_zhi(zhi)
            self.add_star2gong(star_item, gong)
            zhi = Zhi((zhi.value + self.is_forward) % 12)

    def set_zhi_stars(self):
        """
        获取年支系诸星位置（需命宫、身宫信息）
        :param year_zhi: 生年地支
        :param ming_gong: 命宫地支
        :param shen_gong: 身宫地支
        :return: 年支系星位置字典
        """
        
        for star, positions in zhi_based_stars.items():
            star_item = Star(star)
            zhi = Zhi.from_chinese(positions[self.year_zhi.value])
            gong = self.get_gong_by_zhi(zhi)
            self.add_star2gong(star_item, gong)

        
        # 处理天才星：命宫起子顺数到年支
        steps = (self.year_zhi.value + self.ming_zhi.value) % 12
        zhi = Zhi(steps)
        gong = self.get_gong_by_zhi(zhi)
        star_item = Star('天才')
        self.add_star2gong(star_item, gong)
        
        # 处理天寿星：身宫起子顺数到年支
        steps = (self.year_zhi.value + self.shen_zhi.value) % 12
        zhi = Zhi(steps)
        gong = self.get_gong_by_zhi(zhi)
        star_item = Star('天寿')
        self.add_star2gong(star_item, gong)

    def set_tianshang_tianshi(self):
        steps = (5 + self.ming_zhi.value) % 12
        zhi = Zhi(steps)
        gong = self.get_gong_by_zhi(zhi)
        star_item = Star('天伤')
        self.add_star2gong(star_item, gong)
        steps = (7 + self.ming_zhi.value) % 12
        zhi = Zhi(steps)
        gong = self.get_gong_by_zhi(zhi)
        star_item = Star('天使')
        self.add_star2gong(star_item, gong)

    def set_konggong_star(self):
        for gong in self.gong_list:
            if self.check_konggong(gong):
                gong.duigong_star_list = [star for star in gong.duigong.star_list if star.name in main_star_list]

    def check_konggong(self, gong):
        label = False
        for star in gong.star_list:
            if star.name in main_star_list:
                label = True
        return not label
    
    def set_duigong_sanfanggong(self):
        for i in range(12):
            gong = self.gong_list[i]
            gong.duigong = self.gong_list[(i+6)%12]
            gong.sanfanggong.append(self.gong_list[(i+4)%12])
            gong.sanfanggong.append(self.gong_list[(i+8)%12])

    def set_daxian(self):
        start = self.ju_num
        for i in range(12):
            step = (self.ming_zhi.value + i * self.is_forward) % 12
            zhi = Zhi(step)
            gong = self.get_gong_by_zhi(zhi)
            gong.set_daxian((start + i * 10, start + i * 10 + 9))

    def get_benming_info(self):
        word = '# 本命盘报告：\n## 星曜信息'
        for i in range(12):
            step = (self.ming_zhi.value + i * self.is_forward) % 12
            zhi = Zhi(step)
            gong = self.get_gong_by_zhi(zhi)
            word += self.get_benming_info_by_gong(gong)
        word += self.print_benming_hua()
        return word

    def get_benming_info_by_gong(self, gong: Gong):
        word = f'\n宫位：{gong.name[0]} 星宿：{",".join([star.name for star in gong.star_list])} 干支：{gong.gan.chinese_name}{gong.zhi.chinese_name}'
        return word

    def check_hua_by_gan(self):
        self.gan_hua = dict()
        for hua in SI_HUA_MAP:
            self.gan_hua[hua] = dict()
            for i in range(10):
                gan = Gan(i)
                star_item, target_gong = self.check_certain_hua_by_gan(gan, hua)
                self.gan_hua[hua][gan] = (star_item, target_gong)

    def check_hua_by_gong(self):
        self.direct_hua = dict()
        for hua in SI_HUA_MAP:
            self.direct_hua[hua] = []
            for i in range(12):
                zhi = Zhi(i)
                gong = self.get_gong_by_zhi(zhi)
                gan = gong.gan
                (star_item, target_gong) = self.gan_hua[hua][gan]
                self.direct_hua[hua].append((gong, star_item, target_gong))
                target_gong.hua[i].append(hua)
                star_item.hua.append(hua)

    def check_lujichengshuang(self):
        self.lujichengshuang = []
        for hua_lu_comb in self.direct_hua["禄"]:
            for hua_ji_comb in self.direct_hua["忌"]:
                star_lu = hua_lu_comb[1]
                star_ji = hua_ji_comb[1]
                if star_lu == star_ji:
                    gong_lu = hua_lu_comb[0]
                    gong_ji = hua_ji_comb[0]
                    target_gong = hua_lu_comb[2]
                    self.lujichengshuang.append((gong_lu, gong_ji, target_gong, star_lu))

    def get_hua_comb_by_gong(self, gong, hua_name):
        comb_list = self.direct_hua[hua_name]
        for comb in comb_list:
            if gong == comb[0]:
                return comb

    def check_certain_hua_by_gan(self, gan, hua_name):
        positions = SI_HUA_MAP[hua_name]
        star_name = positions[gan.value]
        star_item, gong = self.get_star_and_gong_by_star(star_name)
        return star_item, gong

    def check_zhuanlu_zhuanji(self):
        self.zhuan = dict()
        self.get_zhuanlu_zhuanji('禄')
        self.get_zhuanlu_zhuanji('忌')

    def get_zhuanlu_zhuanji(self, hua):
        comb_list = self.direct_hua[hua]
        self.zhuan[hua] = []
        for comb in comb_list:
            if comb[0] != comb[2]:
                comb2 = self.get_hua_comb_by_gong(comb[2], '忌')
                if comb2[0] != comb2[2]:
                    self.zhuan[hua].append((comb[0], comb[2], comb2[2]))

    def print_benming_hua(self):
        word = "\n## 飞星四化信息："
        word += self.print_shengnian_hua()
        word += self.print_gong_hua_comb(self.ming_zhi.value)
        return word

    def print_gong_hua_comb(self, mingzhi, name = ""):
        word = "\n### 宫位飞星四化信息："
        word += self.print_gong_hua(mingzhi, name)
        word += self.print_zhuan_hua(mingzhi, name)
        return word

    def print_shengnian_hua(self):
        word = "\n### 生年四化信息："
        gan = self.year_gan
        for hua in SI_HUA_KEY:
            (star_item, target_gong) = self.gan_hua[hua][gan]
            word += f"\n生年引化{star_item.name}化{hua}入{target_gong.name[0]}"
        return word

    def get_daxian_info(self, daxian_num):
        name = f"第{daxian_num+1}步大限"
        word = f"\n{name}：\n### 星曜信息："
        daxian_ming_zhi_num = (self.ming_zhi.value + daxian_num * self.is_forward) % 12
        for i in range(12):
            step = (self.ming_zhi.value + (daxian_num + i) * self.is_forward) % 12
            zhi = Zhi(step)
            gong = self.get_gong_by_zhi(zhi)
            word += self.get_daxian_liunian_info_by_gong(gong, daxian_ming_zhi_num)
        word += self.print_gong_hua_comb(daxian_ming_zhi_num, name)
        word += self.get_hua_relation(self.ming_zhi.value, daxian_ming_zhi_num, "本命", name)
        return word, daxian_ming_zhi_num

    def get_daxian_liunian_info_by_gong(self, gong: Gong, daxian_ming_zhi_num = 0):
        word = f'\n宫位：{gong.calcu_gong_name(daxian_ming_zhi_num)} 星宿：{",".join([star.name for star in gong.star_list])} 干支：{gong.gan.chinese_name}{gong.zhi.chinese_name}'
        if len(gong.duigong_star_list) > 0:
            word += f'。无主星，借对宫主星{",".join([star.name for star in gong.duigong_star_list])}'
        return word
    
    def get_liunian_info(self, liunian_zhi_value, liunian_num):
        name = f"{liunian_num}年"
        word = f"\n### 星曜信息："
        for i in range(12):
            step = (liunian_zhi_value + i) % 12
            zhi = Zhi(step)
            gong = self.get_gong_by_zhi(zhi)
            word += self.get_daxian_liunian_info_by_gong(gong, liunian_zhi_value)
        word += self.print_gong_hua_comb(liunian_zhi_value, name)
        word += self.get_hua_relation(self.ming_zhi.value, liunian_zhi_value, "本命", name)
        return word

    def print_gong_hua(self, zhi_num, name = ""):
        word = "\n#### 宫位直接飞星四化信息："
        for hua in SI_HUA_KEY:
            for comb in self.direct_hua[hua]:
                (gong, star_item, target_gong) = comb
                word += f"\n{name}{gong.calcu_gong_name(zhi_num)}引化{star_item.name}化{hua}入{name}{target_gong.calcu_gong_name(zhi_num)}"
        return word

    def print_zhuan_hua(self, zhi_num, name = ""):
        word = "\n#### 宫位转禄转忌飞星四化信息："
        for hua in ['禄', '忌']:
            for comb in self.zhuan[hua]:
                (gong1, gong2, gong3) = comb
                word += f"\n{name}{gong1.calcu_gong_name(zhi_num)}由{name}{gong2.calcu_gong_name(zhi_num)}转{hua}入{name}{gong3.calcu_gong_name(zhi_num)}"
        return word
    
    def calcu_current_daxian(self, liunian_num):
        age = liunian_num - self.year_num  + 1
        daxian_num = (age - self.ju_num + 1) // 10
        return daxian_num
    
    def get_hua_relation(self, zhi_num1, zhi_num2, name1, name2):
        word = ""
        word += self.print_gong_hua_relation(zhi_num1, zhi_num2, name1, name2)
        word += self.print_zhuan_hua_relation(zhi_num1, zhi_num2, name1, name2)
        if len(word) > 0:
            return f"\n### {name2}与{name1}四化关系：{word}"

    def print_gong_hua_relation(self, zhi_num1, zhi_num2, name1, name2):
        word = ""
        for hua in SI_HUA_KEY:
            for comb in self.direct_hua[hua]:
                (gong, star_item, target_gong) = comb
                hua_dis = (gong.zhi.value - target_gong.zhi.value) % 12
                pan_dis = (zhi_num1 - zhi_num2) % 12
                if (hua_dis == pan_dis):
                    word += f"\n{name1}{gong.calcu_gong_name(zhi_num1)}引化{star_item.name}化{hua}入{name2}{target_gong.calcu_gong_name(zhi_num2)}"
                if (hua_dis + pan_dis == 12):
                    word += f"\n{name2}{gong.calcu_gong_name(zhi_num2)}引化{star_item.name}化{hua}入{name1}{target_gong.calcu_gong_name(zhi_num1)}"
        return word

    def print_zhuan_hua_relation(self, zhi_num1, zhi_num2, name1, name2):
        word = ""
        for hua in ['禄', '忌']:
            for comb in self.zhuan[hua]:
                (gong1, gong2, gong3) = comb
                hua_dis = (gong1.zhi.value - gong3.zhi.value) % 12
                pan_dis = (zhi_num1 - zhi_num2) % 12
                if (hua_dis == pan_dis):
                    word += f"\n{name1}{gong1.calcu_gong_name(zhi_num1)}由{name1}{gong2.calcu_gong_name(zhi_num1)}/{name2}{gong2.calcu_gong_name(zhi_num2)}转{hua}入{name2}{gong3.calcu_gong_name(zhi_num2)}"
                if (hua_dis + pan_dis == 12):
                    word += f"\n{name2}{gong1.calcu_gong_name(zhi_num2)}由{name1}{gong2.calcu_gong_name(zhi_num1)}/{name2}{gong2.calcu_gong_name(zhi_num2)}转{hua}入{name1}{gong3.calcu_gong_name(zhi_num1)}"
        return word
    
    def calcu_liunian_zhi(self, liunian_num):
        zhi_num = (liunian_num - self.year_num + self.year_zhi.value) % 12
        return zhi_num

    def get_liunian_daxian_info_comb(self, liunian_num):
        word = f"\n\n# {liunian_num}年分析结果："
        daxian_num = self.calcu_current_daxian(liunian_num)
        is_in_daxian = daxian_num >= 0
        if is_in_daxian:
            daxian_info, daxian_mingzhi_num = self.get_daxian_info(daxian_num)
            word += f"\n## 所在大限信息：{daxian_info}"
        liunian_mingzhi_num = self.calcu_liunian_zhi(liunian_num)
        liunina_info = self.get_liunian_info(liunian_mingzhi_num, liunian_num)
        word += f"\n## 所在流年信息：{liunina_info}"
        if is_in_daxian:
            word += self.get_hua_relation(daxian_mingzhi_num, liunian_mingzhi_num, f"第{daxian_num+1}步大限", f"{liunian_num}年")
            word += self.print_lujichengshuang(daxian_mingzhi_num, liunian_mingzhi_num, f"第{daxian_num+1}步大限", f"{liunian_num}年")
        return word
    
    def print_lujichengshuang(self, zhi_num1, zhi_num2, name1, name2):
        word = f"\n# 禄忌成双结果："
        for item in self.lujichengshuang:
            gong_lu = item[0]
            gong_ji = item[1]
            via_gong = item[2]
            star = item[3]
            word += f"\n{name2}{gong_ji.calcu_gong_name(zhi_num2)}引化{star.name}化忌，劫本命{gong_lu.name[0]}/{name1}{gong_lu.calcu_gong_name(zhi_num1)}引化{star.name}化禄，需要考虑这一年是否有资源/钱财被劫或者获得的情况。"
        return word
        

    

