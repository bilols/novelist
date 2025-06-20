# engine/logconf.py
import logging, sys, pathlib, datetime

LOG_DIR = pathlib.Path(__file__).resolve().parents[1] / "outputs" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def init(level: str = "INFO"):
    """Configure root logger once per run."""
    fmt = "%(asctime)s | %(levelname)-5s | %(module)s | %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), 20),
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                LOG_DIR / f"driver_{datetime.date.today()}.log", encoding="utf-8"
            ),
        ],
        force=True,
    )

def get_logger(name: str):
    return logging.getLogger(name)
