import logging
from common.utils import is_valid_destination_file_path

def get_logger(func_name: str, log_file_path: str) -> logging.Logger:


    if not is_valid_destination_file_path(log_file_path):
        raise ValueError(f"Invalid log file path: {log_file_path}")
    
    logger = logging.getLogger(func_name)
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers:
        handler = logging.FileHandler(log_file_path, mode='a')
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

def flush_logger(logger: logging.Logger) -> None:
    for handler in logger.handlers:
        handler.flush()