from .const import VALIDYAO
# VALIDYAO = [0, 1]
class YaoGenerator():
    value = -1

    def __init__(self, biList):
        if (biList is None or len(biList) != 3):
            print("Invalid input")
            return
        for item in biList:
            if item not in VALIDYAO:
                print("Invalid input")
                return
        self.value = 0
        for item in biList:
            self.value *= 2
            self.value += item
