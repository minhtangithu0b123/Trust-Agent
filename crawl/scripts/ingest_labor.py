import logging

from app.config import get_settings
from app.vectorstore import ingest_labor


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(ingest_labor(get_settings()))
