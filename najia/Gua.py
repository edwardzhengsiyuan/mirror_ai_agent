from .const import YANGYAO, LIUSHISIGUA, BAGUA, BIANYAO, LIUSHENDICT, XUNKONGDICT, DIZHIWUXING, LIUQINLIST, LIUSHISIGUAINFO, DIZHI, SWMJIDX, WXXQSPOWER, LIUSHISIGUAVALUE
import time
import numpy as np
from .TimeInfoGenerator import CurrentTimeInfoGenerator
import math

class Gua():
    value = -1
    name = ''
    yaoYinyangList = [0 for _ in range(6)]
    def __init__(self, value, name = None, yaoYinyangList = None) -> None:
        self.value = value
        if yaoYinyangList is not None:
            self.yaoYinyangList = yaoYinyangList
        else:
            for i in range(6):
                self.yaoYinyangList[5-i] = value % 2
                value //= 2
        if name is not None:
            self.name = name
        else:
            xiagua = self.value // 8
            shanggua = self.value % 8
            self.name = LIUSHISIGUA[xiagua][shanggua]

class LiushisiGua(Gua):
    wuxing = None
    najia = []
    liuqin = []
    shiyao = -1
    yingyao = -1
    fullname = ""
    gong = ""
    gongwei = ""
    
    def __init__(self, value, name = None, yaoYinyangList = None):
        super(LiushisiGua, self).__init__(value, name, yaoYinyangList)
        self.getBasicInfo()

    def getBasicInfo(self):
        info = LIUSHISIGUAINFO[self.name]
        self.wuxing = info["wuxing"]
        self.najia = info["najia"]
        self.shiyao = info["shiyao"]
        self.yingyao = info["yingyao"]
        self.fullname = info["fullname"]
        self.gong = info["gong"]
        self.gongwei = info["gongwei"]
        
    def getLiuqin(self, guaWuxing):
        guaWuxingArray = np.array([guaWuxing.value for _ in range(6)])
        zhiWuxingArray = np.array([DIZHIWUXING[self.najia[i][1]].value for i in range(6)])
        liuqingArray = zhiWuxingArray - guaWuxingArray
        liuqingIdxList = list(liuqingArray)
        self.liuqin = [LIUQINLIST[i] for i in liuqingIdxList]

    def printGua(self):
        print(f'{self.fullname}卦')
        print(f'{self.gong}宫{self.gongwei}卦')
        yaoYinyangList = self.yaoYinyangList
        for i in range(6):
            newi = 5-i
            print(self.najia[newi], end = "")
            print(self.liuqin[newi], end = "")
            if yaoYinyangList[newi] == 1:
                print("---", end = "")
            if yaoYinyangList[newi] == 0:
                print("- -", end = "")
            if self.shiyao == newi:
                print("世", end = "")
            if self.yingyao == newi:
                print("应", end = "")
            print("\n")

class BenGua(LiushisiGua):
    bianyaoList = [0 for _ in range(6)]
    biangua = None
    hasTimeInfo = False
    bazi = None
    liushen = None
    xunkong = None
    
    def __init__(self, value, name = None, yaoYinyangList = None, bianyaoList = None, bazi = None, liushen = None, xunkong = None):
        super(BenGua, self).__init__(value, name, yaoYinyangList)
        self.bianyaoList = bianyaoList
        self.getLiuqin(self.wuxing)
        self.fushenLiuqin = ["" for _ in range(6)]
        self.fushenNajia = ["" for _ in range(6)]
        if (bazi is not None):
            self.hasTimeInfo = True
        if (self.hasTimeInfo):
            self.bazi = bazi
            self.liushen = liushen
            self.xunkong = xunkong
        if self.name != self.gong:
            self.getFushen()

    def printGua(self):
        print(f'{self.fullname}卦')
        print(f'{self.gong}宫{self.gongwei}卦')
        yaoYinyangList = self.yaoYinyangList
        for i in range(6):
            newi = 5-i
            print(self.liushen[newi], end = "")
            print(self.najia[newi], end = "")
            print(self.liuqin[newi], end = "")
            if yaoYinyangList[newi] == 1:
                print("---", end = "")
            if yaoYinyangList[newi] == 0:
                print("- -", end = "")
            if self.bianyaoList[newi] == 1:
                print("x", end = "")
            if self.shiyao == newi:
                print("世", end = "")
            if self.yingyao == newi:
                print("应", end = "")
            if len(self.fushenLiuqin[newi] + self.fushenNajia[newi]) > 0:
                print(f"[伏{self.fushenLiuqin[newi]}{self.fushenNajia[newi]}]", end = "")
            print("\n")

    def getBiangua(self):
        bianguaList = list(np.bitwise_xor(np.array(self.yaoYinyangList), np.array(self.bianyaoList)))
        xiaguaValue = 0
        shangguaValue = 0
        for item in bianguaList[:3]:
            xiaguaValue *= 2
            xiaguaValue += item
        for item in bianguaList[3:]:
            shangguaValue *= 2
            shangguaValue += item
        bianguaValue = xiaguaValue * 8 + shangguaValue
        bianguaName = LIUSHISIGUA[xiaguaValue][shangguaValue]
        self.biangua = BianGua(bianguaValue, bianguaName, bianguaList, self.wuxing)
        return self.biangua
    
    def getFushen(self):
        bengongValue = LIUSHISIGUAVALUE[self.gong]
        self.bengongGua = LiushisiGua(bengongValue, self.gong)
        self.bengongGua.getLiuqin(self.wuxing)
        for i in range(6):
            if self.bengongGua.liuqin[i] not in self.liuqin:
                self.fushenLiuqin[i] = self.bengongGua.liuqin[i]
                self.fushenNajia[i] = self.bengongGua.najia[i]
    
    def printBiangua(self):
        self.biangua.printGua()

class BianGua(LiushisiGua):
    def __init__(self, value, name, yaoYinyangList, benguaWuxing):
        super(BianGua, self).__init__(value, name, yaoYinyangList)
        self.getLiuqin(benguaWuxing)

class GuaGenerator():
    selfgua = None
    xiagua = None
    shanggua = None
    bianyaoList = [0 for _ in range(6)]
    bazi = None
    liushen = None
    xunkong = None

    def __init__(self, yaoList):
        self.selfgua = None
        self.xiagua = None
        self.shanggua = None
        self.bianyaoList = [0 for _ in range(6)]
        self.generateTimeRelatedInfo()
        if yaoList is None or len(yaoList) != 6:
            print("Invalid input")
            return
        for yaoValue in yaoList:
            if yaoValue not in range(8):
                print("Invalid input")
                return
        selfValue = 0
        xiaguaValue = 0
        shangguaValue = 0
        yaoYinyangList = [0 for _ in range(6)]
        for yaoValue in yaoList[:3]:
            xiaguaValue *= 2
            xiaguaValue += 1 if yaoValue in YANGYAO else 0
        for yaoValue in yaoList[3:]:
            shangguaValue *= 2
            shangguaValue += 1 if yaoValue in YANGYAO else 0
        for i in range(6):
            if yaoList[i] in BIANYAO:
                self.bianyaoList[i] = 1
            yaoYinyangList[i] = 1 if yaoList[i] in YANGYAO else 0
        xiaguaName = BAGUA[xiaguaValue]
        shangguaName = BAGUA[shangguaValue]
        selfValue = xiaguaValue * 8 + shangguaValue
        selfName = LIUSHISIGUA[xiaguaValue][shangguaValue]
        self.selfgua = BenGua(selfValue, selfName, yaoYinyangList, self.bianyaoList, self.bazi, self.liushen, self.xunkong)
        self.xiagua = Gua(xiaguaValue, xiaguaName, yaoYinyangList[:3])
        self.shanggua = Gua(shangguaValue, shangguaName, yaoYinyangList[3:])

    def generateTimeRelatedInfo(self):
        currentTime = CurrentTimeInfoGenerator()
        self.bazi = currentTime.bazi
        self.year = self.bazi.getYear()
        self.month = self.bazi.getMonth()
        self.day = self.bazi.getDay()
        self.hour = self.bazi.getTime()
        self.time_info = f'{self.year}年{self.month}月{self.day}日{self.hour}时'
        self.liushen = LIUSHENDICT[self.day[0]]
        self.xunkong = XUNKONGDICT[self.day]
        print(self.time_info)
        
class GuaAnalyzer:
    gua = None
    yongshen = ""
    bazi = None
    
    def __init__(self, value, yongshen) -> None:
        self.gua = BenGua(value)
        self.yongshen = yongshen
        
    def getYyjc(self):
        idx = LIUQINLIST.index(self.yongshen)
        yuanshen = LIUQINLIST[idx - 1]
        jishen = LIUQINLIST[idx - 2]
        choushen = LIUQINLIST[idx - 3]
        
    def getPower(self, dizhi, yao):
        dizhiIdx = DIZHI.idx(dizhi)
        dizhiWuxing = DIZHIWUXING[dizhi]
        dizhiWuxingIdx = dizhiWuxing.value
        yaoDizhi = yao[1]
        yaoWuxing = DIZHIWUXING[yaoDizhi]
        yaoWuxingIdx = yaoWuxing.value
        x = dizhiIdx * np.pi / 6 + np.pi / 12
        powerSwmj = np.cos(x - np.pi/4 * SWMJIDX[yaoWuxingIdx]) / 2 + 0.5
        powerWxxqs = WXXQSPOWER[yaoWuxingIdx - dizhiWuxingIdx]
        power = (powerSwmj + powerWxxqs) / 2
        
    def getJintui(self, ben, bian):
        benZhi = ben[1]
        bianZhi = bian[1]
        benIdx = DIZHI.index(benZhi)
        bianIdx = DIZHI.index(bianZhi)
        yuezhi = self.bazi.getMonthZhi()
        rizhi = self.bazi.getDayZhi()
        yuepo = self.getZhiChong(yuezhi)
        ripo = self.getZhiChong(rizhi)
        if ((bianIdx - benIdx) % 12 <= 6):
            if (bianZhi in [yuepo, ripo]):
                if bianZhi == yuepo:
                    po = "月"
                else:
                    po = "日"
                return f"变爻{bian}逢{po}破，不进。"
            elif (benZhi in [yuepo, ripo]):
                if benZhi == yuepo:
                    po = "月"
                else:
                    po = "日"
                return f"动爻{ben}逢{po}破，不能进。"
            else:
                return f"{ben}变{bian}为进神。"
        elif ((bianIdx - benIdx) % 12 > 6):
            if (bianZhi in [yuepo, ripo]):
                if bianZhi == yuepo:
                    po = "月"
                else:
                    po = "日"
                return f"变爻{bian}逢{po}破，不退。"
            elif (benZhi in [yuepo, ripo]):
                if benZhi == yuepo:
                    po = "月"
                else:
                    po = "日"
                return f"动爻{ben}逢{po}破，不能退。"
            else:
                return f"{ben}变{bian}为退神。"
        
    def getZhiChong(self, zhi):
        idx = DIZHI.index(zhi)
        return DIZHI[idx - 6]
        
    def generateTimeRelatedInfo(self):
        currentTime = CurrentTimeInfoGenerator()
        self.bazi = currentTime.getEightChar()
        rigan = self.bazi.getDayGan()
        liushen = LIUSHENDICT[rigan]
        rizhu = self.bazi.getDay()
        xunkong = XUNKONGDICT[rizhu]
