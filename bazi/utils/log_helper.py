# utils/log_helper.py

import logging

class LogHelper:
    def __init__(self, name='bazi_analysis', level=logging.INFO):
        self.ans = ''
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        # 创建格式器并添加到处理器
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)

        # 如果 logger 还没有处理器，添加处理器
        if not self.logger.handlers:
            self.logger.addHandler(console_handler)
            self.logger.propagate = False  # 防止日志冒泡重复输出

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.ans += message
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)
