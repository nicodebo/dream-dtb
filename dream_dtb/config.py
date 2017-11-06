import os
import tempfile
from uuid import uuid4
from gi.repository import GLib

# script dir
ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

# database
DB_NAME = 'dream.db'
# configuration file
CF_NAME = 'dreamrc'
# log file
LOG_NAME = 'dream.log'
# socket name for nvim rpc communication
SOCK_NAME = f'nvim-{uuid4()}'

# directory to be included in nvim runtimepath variable that provide custom rpc
# events
NVIM_RUNTIME = os.path.join(ROOT_DIR, 'runtime')

# xdg base directory
try:
    CONF_PATH = os.path.join(os.environ['XDG_CONFIG_HOME'], 'dreamdtb', CF_NAME)
except KeyError:
    CONF_PATH = os.path.join(os.environ['HOME'], '.config', 'dreamdtb', CF_NAME)

try:
    DB_PATH = os.path.join(os.environ['XDG_DATA_HOME'], 'dreamdtb', DB_NAME)
except KeyError:
    DB_PATH = os.path.join(os.environ['HOME'], '.local', 'share', 'dreamdtb', DB_NAME)

try:
    LOG_PATH = os.path.join(os.environ['XDG_CACHE_HOME'], 'dreamdtb', LOG_NAME)
except KeyError:
    LOG_PATH = os.path.join(os.environ['HOME'], '.cache', 'dreamdtb', LOG_NAME)

try:
    IPC_PATH = os.path.join(os.environ['XDG_RUNTIME_DIR'], 'dreamdtb', SOCK_NAME)
except KeyError:
    IPC_PATH = os.path.join(GLib.get_tmp_dir(), 'dreamdtb', SOCK_NAME)


BUF_PATH = tempfile.mkdtemp(prefix='dreamdtb')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s :: %(asctime)s :: %(module)s :: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '%(levelname)s :: %(message)s'
        }
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': LOG_PATH,
            'maxBytes': 1000000,
            'backupCount': 1,
            'mode': 'a'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout'
        },
    },
    'loggers': {
        'dream_logger': {
            'handlers': ['console', 'file'],
            # 'propagate': False,
            'level': 'DEBUG'
        }
    },
    # 'root': {
    #     'handlers': ['console', 'file'],
    #     'level': 'DEBUG'
    # }
}
