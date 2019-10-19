# -*- coding: utf-8 -*-

from logging import StreamHandler
from logging.handlers import RotatingFileHandler
from collections import namedtuple, deque
from pathlib import Path
from multiprocessing import Lock, Value
from enum import Enum
import logging
import json
import sys
import os


# Switches
class Switch(Enum):
    LIGHT = 0
    IR_LIGHT = 1
    FAN = 2


# Setup logging
APP_LOGGER_BUFFER_SIZE: int = 200


# Environments
class Environment(Enum):
    DEV = 0     # Development
    PROD = 1    # On yasc


# Get system environment variables and setup application for dev or production
def __setup_environment() -> Environment:
    env_var: str = os.getenv('OWLCAM_ENV', '')
    if env_var is None:
        logging.error('Environment variable OWLCAM_ENV not defined!')
        logging.error('Setting environment to DEV!')
        return Environment.DEV
    else:
        try:
            return Environment[env_var.upper()]
        except ValueError:
            logging.error('Unrecognized environment variable OWLCAM_ENV with value {0}.'.format(env_var))
            logging.error('Setting environment to DEV!')
            return Environment.DEV


_ENVIRONMENT = __setup_environment()


def in_development() -> bool:
    return _ENVIRONMENT == Environment.DEV


def in_production() -> bool:
    return _ENVIRONMENT == Environment.PROD


APP_PATH = Path('.').resolve()
logging.info('Application file paht is {0}'.format(APP_PATH.absolute()))


# Read config file
CONFIG: object = None


def get_project_path() -> Path:
    return Path('.').resolve()


try:
    config_file = Path('config_{0}.json'.format(_ENVIRONMENT.name.lower())).resolve()
    with config_file.open() as file:
        config_str = file.read()
        CONFIG = json.loads(config_str, object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))
except FileNotFoundError:
    logging.error('Config file {0} does not exist!'.format(config_file))
    sys.exit(1)
else:
    logging.info('Loaded config {0}.'.format(config_file.name))
    logging.info(json.dumps(json.loads(config_str), indent=2, sort_keys=True))


# Setup logger
class AppLogHandler(StreamHandler):
    def __init__(self):
        super(StreamHandler, self).__init__()
        self.__queue  = deque([], APP_LOGGER_BUFFER_SIZE)
        self.__counter = Value('i', 0)
        self.__lock = Lock()

    def emit(self, record):
        with self.__lock:
            self.__counter.value += 1
        self.__queue.append(self.format(record))

    def flush(self):
        pass

    def get_logs(self, offset=0):
        with self.__lock:
            delta = self.__counter.value - offset
            delta = 0 if delta < 0 else delta
            delta = APP_LOGGER_BUFFER_SIZE if delta > APP_LOGGER_BUFFER_SIZE else delta
            logs = [] if delta == 0 else [e for e in self.__queue.copy()]
            return logs


APP_LOG_HANDLER: AppLogHandler = AppLogHandler()
GLOBAL_LOG_HANDLER: StreamHandler

log_level_str = os.getenv('OWLCAM_LOG_LEVEL', None)
log_level = logging.INFO
if log_level_str is not None:
    log_level = logging.getLevelName(log_level_str.upper())


logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
rootLogger = logging.getLogger()
rootLogger.setLevel(log_level)

env: str = os.getenv('OWLCAM_ENV', '')
if env is not None and Environment[env.upper()] == Environment.PROD:
    GLOBAL_LOG_HANDLER = RotatingFileHandler("{0}/{1}.log".format('.', 'owlcam'), maxBytes=10000000, backupCount=5)
    GLOBAL_LOG_HANDLER.setFormatter(logFormatter)
    rootLogger.addHandler(GLOBAL_LOG_HANDLER)
else:
    GLOBAL_LOG_HANDLER = logging.StreamHandler()
    GLOBAL_LOG_HANDLER.setFormatter(logFormatter)
    rootLogger.addHandler(GLOBAL_LOG_HANDLER)

APP_LOG_HANDLER.setFormatter(logFormatter)
rootLogger.addHandler(APP_LOG_HANDLER)


