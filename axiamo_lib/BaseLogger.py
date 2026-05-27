import logging
from logging import FileHandler

class BufferHandler(logging.Handler):
    def __init__(self, limit_bytes=10*1024):
        super().__init__()
        self.limit_bytes = limit_bytes
        self.buffer = []

    def emit(self, record):
        msg = self.format(record)
        self.buffer.insert(0,str(msg))

        # Check buffer size and truncate if necessary
        buffer_size = sum(len(entry.encode('utf-8')) for entry in self.buffer)
        if buffer_size > self.limit_bytes:
            excess_bytes = buffer_size - self.limit_bytes
            self.buffer = self.buffer[-excess_bytes:]


def addBufferLogger():
    root_logger = get_custom_logger()
    buffer_handler = BufferHandler()
    root_logger.addHandler(buffer_handler)
    return buffer_handler

def get_custom_logger(log_file='AxiamoX2_Host.log', log_level=logging.INFO, log_format='%(asctime)s - %(levelname)s - %(message)s'):
    logger = logging.getLogger('custom_logger')
    logger.setLevel(log_level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    file_handler = FileHandler(log_file)
    file_handler.setLevel(log_level)
    formatter = logging.Formatter(log_format)
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

Logger = get_custom_logger()