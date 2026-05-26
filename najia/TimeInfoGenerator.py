from lunar_python import Lunar, Solar
from datetime import datetime

class CurrentTimeInfoGenerator:
    lunar = None
    bazi = None
    liushen_list = {
        "甲": ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"],
        "乙": ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"],
        "丙": ["朱雀", "勾陈", "螣蛇", "白虎", "玄武", "青龙"],
        "丁": ["朱雀", "勾陈", "螣蛇", "白虎", "玄武", "青龙"],
        "戊": ["勾陈", "螣蛇", "白虎", "玄武", "青龙", "朱雀"],
        "己": ["螣蛇", "白虎", "玄武", "青龙", "朱雀", "勾陈"],
        "庚": ["白虎", "玄武", "青龙", "朱雀", "勾陈", "螣蛇"],
        "辛": ["白虎", "玄武", "青龙", "朱雀", "勾陈", "螣蛇"],
        "壬": ["玄武", "青龙", "朱雀", "勾陈", "螣蛇", "白虎"],
        "癸": ["玄武", "青龙", "朱雀", "勾陈", "螣蛇", "白虎"],
    }

    def __init__(self) -> None:
        solar = Solar.fromDate(datetime.now())
        self.lunar = solar.getLunar()
        self.bazi = self.lunar.getEightChar()
        self.bazi.setSect(1)

    def get_current_time_info(self):
        return (self.time_info, self.liushen)