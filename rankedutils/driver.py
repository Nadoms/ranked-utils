from pathlib import Path
from os import getenv

from dotenv import load_dotenv

from . import constants, db, api


def initialise(
    db_path: Path = constants.DB_PATH,
    env_path: Path = constants.ENV_PATH,
):
    constants.DB_PATH = db_path
    constants.ENV_PATH = env_path
    api.Match._conn, api.Match._cursor = db.start(db_path)
    load_dotenv(constants.ENV_PATH)
    api.API_KEY = getenv("API_KEY")
