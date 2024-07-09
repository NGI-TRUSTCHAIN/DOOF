#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024


import json
import os 
import socket
import sys
import threading, queue
from threading import Thread
import time


from provider.python.logger.logger_provider import loggerProvider 

from common.python.error import DopError
from common.python.threads import DopStopEvent
from common.python.utils import DopUtils 

class stdStreamLogger(loggerProvider):
    """
    loggingProvider:
        path: '.../std_stream_logger.py'
        class: 'stdStreamLogger'
        configuration: 'loglevel=5;name=23;qsize=10000'
    """

    def __init__(self):
        super().__init__()
        self._logger = None 
        self._connstring = None
        self._name = None
        self._loglevel = ''
        self._conf = 0
        self._queue_size = None
        # Info for logs
        self._hostname = socket.gethostname()
        self._PID = os.getpid()

        self._innerStopEvent = DopStopEvent()
        self._log_queue = queue.Queue()
        self._log_loop = None

    
    def init(self, connstring) -> DopError:
        """

        Connstring should indicate:
            - name/id of component: 21 - client; 22 - DOP gateway; 23 - bridge; 24 - worker; 25 - monitor
            - log_level  (from 0 (none), to 5): indicates max severity level to be processed; NUM1-NUM2 indicates a range
            - qsize: indicates how many log messages can the synchronized queue contain (useful for thread-safe logging)
            # Supports range for the severity levels and not only number; number will have to 
            indicate only the specific level to be printed

            Examples: 
                log_level:1-3		 	will propagate logs with severity level x with 1<=x<=3
                log_level:1-3,10		severity level x where 1<=x<=3 || x==10
                log_level:3-6,10-11		severity level x where 3<=x<=6 || 10<=x<=11

        connstring: 'name=24;log_level=4;'
        
        loglevel: 
        0 NONE
        5 DEBUG
        4 INFO
        3 WARN
        2 ERROR
        1 FATAL/CRITICAL
        """

        self._connstring = connstring
        
        tupleConfig = DopUtils.config_to_dict(connstring)
        if tupleConfig[0].isError():
            
            self._on_error(tupleConfig[0])
            return tupleConfig[0]
        
        
        d_config: dict = tupleConfig[1]
        has_name, self._name = DopUtils.config_get_string(d_config, ['name'], None)
        has_level, self._loglevel = DopUtils.config_get_string(d_config, ['loglevel'], "0")
        has_maxsize, self._queue_size = DopUtils.config_get_string(d_config, ['qsize'], 1000)
        
        self._conf = loggerProvider.get_all_levels(self._loglevel)

        return DopError()
    
    def open(self) -> DopError:
        self._log_loop = Thread(target = self._consume_queue, args=())
        print(f"std_stream open TID:{threading.current_thread().ident}")
        self._log_loop.start()
        return DopError()

    def close(self) -> DopError:
        print("Closing std_stream_logger")
        self._innerStopEvent.stop()
        while True:
            self._log_loop.join(1)
            if not(self._log_loop.is_alive()):
                break
        return DopError()


    def log(self, log_msg_code, sev_level,
            fname,
            lineno, 
            opt_properties:dict={}):
        """
        Enrichment done by LoggerProvider:
        *Timestamp (UNIX seconds from epoch)
        *IP/hostname where the log is generated
        *PID of the process that generated the log (the current process)

        Output:
        Timestamp,IP/hostname,PID,log_msg_code,severity_lev,fname,lineno,optional_properties

        """
        err_lev = loggerProvider.get_log_level_bm(sev_level.value)

        if (self._conf & err_lev): 
            fname = fname.split(os.path.sep)[-1] 

            # seconds from epoch 
            timestamp = int(time.time())
            tid = threading.current_thread().ident
            # NOTE The following syntax is not definitive; take it as a guideline
            log_msg = f"{timestamp}; {self._hostname}; {self._PID}; {tid}; {fname}; {lineno}; MSG_CODE: {log_msg_code}; " + \
                f"SEVERITY: {sev_level}; Properties: {json.dumps(opt_properties)}"
            try:
                #self._log_queue.put_nowait(log_msg)
                self._log_queue.put(log_msg, block=True, timeout=1)
            except queue.Full:
                pass


    def _consume_queue(self):
        
        print(f"Consume queue TID:{threading.current_thread().ident}")
        
        while True:
            
            time.sleep(0)
            entry = 0
            try:
               #entry = self._log_queue.get_nowait() # non blocking
               entry = self._log_queue.get(block=True, timeout=1)
            except queue.Empty:
                pass

            if entry:
                print(entry)
                sys.stdout.flush()
            
            if self._innerStopEvent.is_exiting():
                break

        # Log any remaining messages in the queue
        while True: 
            print("Logging last messages")
            entry = 0
            try:
                entry = self._log_queue.get_nowait()
                #entry = self._log_queue.get(block=True, timeout=1) # non blocking
            except queue.Empty:
                break

            if entry:
                print(entry)
                sys.stdout.flush()

        print("Finishing log consuming thread")