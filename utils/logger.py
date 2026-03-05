import logging
import sys
from pathlib import Path


def setup_logger(name: str = "stock-auto-trade", log_dir: str = "logs") -> logging.Logger:
    """로거 설정 및 반환.

    파일 로그: DEBUG 이상 (logs/YYYY-MM-DD.log)
    콘솔 로그: INFO 이상
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 콘솔 핸들러 (INFO 이상)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 핸들러 (DEBUG 이상)
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    from datetime import date

    file_handler = logging.FileHandler(
        log_path / f"{date.today().isoformat()}.log",
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
