#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

from abc import abstractmethod

from provider.python.provider import Provider

class loggerProvider(Provider):
    """
    loggingProvider:
        path: '.../std_stream_logger.py'
        class: 'stdStreamLogger'
        configuration: 'loglevel=5;name=encryption_worker(or component id: 24);qsize'
    """

    LOG_LEVELS = {
        0:  0b0000000000000000,
        1:  0b0000000000000001,
        2:  0b0000000000000010,
        3:  0b0000000000000100,
        4:  0b0000000000001000,
        5:  0b0000000000010000,
        6:  0b0000000000100000,
        7:  0b0000000001000000,
        8:  0b0000000010000000,
        9:  0b0000000100000000,
        10: 0b0000001000000000,
        11: 0b0000010000000000,
        12: 0b0000100000000000,
        13: 0b0001000000000000,
        14: 0b0010000000000000,
        15: 0b0100000000000000,
        16: 0b1000000000000000
    }


    def __init__(self):
        super().__init__()
        
    # on_error
    # on_data
    # userdata
    # init
    # open
    # close
    # stopEvent 
    # ... 


    @staticmethod
    def get_log_level_bm(x):
        return loggerProvider.LOG_LEVELS.get(x,-1)

    @staticmethod
    def get_all_levels(conf_log_level: str) -> int:
        conf = 0
        for item in conf_log_level.split(','): 
            # check if there is a '-' (in which case log if severity_level is between first and second value)
            if '-' in item:
                min_max = item.split('-')
                min = int(min_max[0])
                max = int(min_max[1])
                for x in range(min, max+1):
                    conf |= loggerProvider.get_log_level_bm(x)
            else:
                conf |= loggerProvider.get_log_level_bm(int(item))

        return conf

    @abstractmethod
    def log(self, log_msg_code, sev_level, fname, lineno, opt_properties:dict={}):
        """
        Enrichment done by LoggerProvider:
        *Timestamp (UNIX seconds from epoch)
        *IP/hostname where the log is generated
        *PID of the process that generated the log (the current process)

        Output:
        Timestamp,IP/hostname,PID,log_msg_code,severity_lev,fname,lineno,optional_properties

        """
    