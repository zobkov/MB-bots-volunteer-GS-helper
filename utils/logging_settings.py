import sys
from datetime import datetime
import os

LOG_DIR = os.path.join(os.path.dirname(__file__), '../../logs')
os.makedirs(LOG_DIR, exist_ok=True)  

logging_config = {
    'version': 1,
    'disable_existing_loggers': False,  # Allow existing loggers to propagate
    'formatters': {
        'formatter_2': {
            'format': '#%(levelname)-8s [%(asctime)s] - %(filename)s:'
                      '%(lineno)d - %(name)s:%(funcName)s - %(message)s'
        }
    },
    'handlers': {
        'stdout': {
            'class': 'logging.StreamHandler',
            'formatter': 'formatter_2',
            'stream': sys.stdout
        }
    },
    'root': {
        'handlers': ['stdout', 'file'],
        'level': 'DEBUG'
    },
    'loggers': {
        'aiogram': {
            'handlers': ['stdout', 'file'],
            'level': 'INFO',  # Keep default level for general aiogram logs
            'propagate': False
        },
        'aiogram.event': {
            'handlers': ['stdout', 'file'],
            'level': 'DEBUG',  # Set only event handling logs to DEBUG
            'propagate': False
        }
    }
}