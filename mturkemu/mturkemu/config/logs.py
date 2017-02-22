import os.path

def GenerateLoggingConfig(LOG_DIR):
    return(
        {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters' : {
                'mturk_fmt' : {
                    "format" : "%(asctime)s|%(levelname)s|%(message)s",
                },
            },
            'handlers': {
                'terminal' : {
                    'level': 'INFO',
                    'class' : 'logging.StreamHandler',
                },
                'auth_handler' : {
                    "level" : "INFO",
                    "class" : "logging.FileHandler",
                    "filename" : os.path.join(LOG_DIR, "auth.log"),
                },
                'mturk': {
                    'level': 'INFO',
                    'class': 'logging.FileHandler',
                    'filename': os.path.join(LOG_DIR,"mturk.log"),
                },
                'commission_handler' : {
                    "level" : "INFO",
                    "class" : "logging.FileHandler",
                    "filename" : os.path.join(LOG_DIR, "commission.log"),
                },
            },
            'loggers': {
                'django.request': {
                    'handlers': ['mturk'],
                    'level': 'DEBUG',
                    'propagate': True,
                },
                'django.auth' : {
                    "handlers" : ["auth_handler"],
                    "level" : "INFO",
                    "propogate" : False
                },
                'mturk' : {
                    'handlers' : ['mturk'],
                    "level" : "INFO",
                    "propagate" : True,
                },
                'commission' : {
                    'handlers' : ['commission_handler', 'terminal'],
                    "level" : "INFO",
                    "propagate" : True,
                },
            },
        }
    )
