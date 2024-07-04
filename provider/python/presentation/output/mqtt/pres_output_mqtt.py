#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   ver:    1.2
#   date:   17/04/2024
#   author: georgiana-bud


# ver 1.2 
# - method for writing output to endpoint 

# Additions ver. 1.1
# - subclass of MQTT.Client and re-definition of loop_stop method 
# - addition of a delay between successive trials of reconnection


import json
import sys

import os
import hashlib
import paho.mqtt.client as mqtt
import time
import threading
from threading import Event, Thread
import uuid

from provider.python.presentation.output.provider_pres_output import outputPresentationProvider
from common.python.error import DopError
from common.python.event import DopEvent
from common.python.utils import DopUtils

from inspect import currentframe, getframeinfo
import traceback
MQTTv311 = 4

class Client(mqtt.Client):
    def __init__(self, client_id="", clean_session=None, userdata=None,
                 protocol=MQTTv311, transport="tcp", reconnect_on_failure=True):
        
        super().__init__(client_id, clean_session, userdata, protocol,
                        transport, reconnect_on_failure)
        

    def loop_stop(self):
        super().loop_stop()
        self._reset_sockets(sockpair_only=True)

class outputMqttPaho(outputPresentationProvider):
    
    # as in inputMqttPaho
    def __init__(self):
        self._output_client = None
        #self._client_id: str = "hjkhjkhjkhjkhjk"
        self._client_session: bool = False
        self._protocol = mqtt.MQTTv311
        self._transport: str = "tcp"                  #   could be websocket (if set to websocket, the logic would be slightly different)
        #self._host: str = "10.170.30.66"
        self._port: int = 1883
        self._keepalive: int = 10
        #self._bind_address: str = ""
        self._qos: int = 1
        #self._topic: str = "test_topic"
        self._configured: bool = False
        self._timeout: int = 20
        self._last_mid: int = 0
        self._max_retries: int = 5
        self._retries_count: int = 0

        self._connection_event: Event = Event()
        self._connection_event.clear()

        super().__init__()


    def init(self,connstring: str) -> DopError:
       
        #   connstring example
        #   host=10.170.30.66;port=1883;topic=test_topic;retrycount=10;keepalive=60;qos=1;timeout=10;prefix=grz_;
        #   h=10.170.30.66;p=1883;t=test_topic;rc=10;ka=60;q=1;tout=10;prf=grz_;
        tupleConfig = DopUtils.config_to_dict(connstring)
        if tupleConfig[0].isError():
            self._on_error(tupleConfig[0])
            return tupleConfig[0]

        #   mandatory parameters
        has_host = False
        has_topic = False
        wfc = False	
        has_prefix = False
        
        d_config: dict = tupleConfig[1]
        has_host, self._host = DopUtils.config_get_string(d_config, ['host','h'], None)

        has_topic, self._topic = DopUtils.config_get_string(d_config, ['topic','t'], None)

        wfc, self._bind_address = DopUtils.config_get_string(d_config,['bindaddress','ba'],"")
        wfc, self._port = DopUtils.config_get_int(d_config,['port','p'],1883)
        wfc, self._max_retries = DopUtils.config_get_int(d_config,['retrycount','rc'],10)
        wfc, self._keepalive = DopUtils.config_get_int(d_config,['keepalive','ka'],60)
        wfc, self._qos = DopUtils.config_get_int(d_config,['qos','q'],1)
        wfc, self._timeout = DopUtils.config_get_int(d_config,['timeout','tout'],20)

            
        wfc, prefix = DopUtils.config_get_string(d_config, ['prefix','prf'], None)

        self._client_id = self.generate_client_id(prefix)
            
        if (has_host and has_topic) == False:
            err = DopError(1,"Configuration missing mandatory parameter(s).")
            self._on_error(err)
            return err

        if (self._qos < 0) or (self._qos>2):
            self._qos = 1
            self._on_error(DopError(0,"invalid qos, using default"))

        if self._timeout < 0:
            self._timeout = 20
            self._on_error(DopError(0,"invalid timeout, using default"))

        self._configured = True 
        self._on_error(DopError(0,"provider configured"))   
        return DopError()

    #       callbacks
    def on_connect(self, client, userdata, flags, rc):
        self._on_error(DopError(0,"connected with result code "+str(rc)))
        if rc != 0:
            #   failure connecting
            self._on_error(DopError(100,"Could not connect to the broker."))
            if self.stopEvent.is_exiting() == False:
                if self._max_retries > self._retries_count:
                    self._retries_count += 1
                    self.open()
            return

        #   signal connection
        self._connection_event.set()  
            

    def on_disconnect(self, client, userdata, rc):
        #self.wait_for_event_status(self._timeout, self._connection_event, False)

        self._connection_event.clear()
        self._output_client.loop_stop()
        if rc != 0:
            self._on_error(DopError(103,f"Unexpected disconnection. Result code {rc}"))

        if self.stopEvent.is_exiting() == False:
            #   no higher-level exit has been signalled
            #   ==> try to reconnect
            time.sleep(1)
            self.open()

    @staticmethod
    def wait_for_event_status(timeout: int, event: Event, status: bool) -> bool:
        """
        waits on event for status
        if timeout expires, the method returns False, True otherwise
        NOTE:       this static method could be moved to a shared/common module
        """
        elapsed: int = 0
        while event.is_set() != status:
            time.sleep(1)
            elapsed += 1
            if elapsed >= timeout:
                return False
        return True


    @staticmethod
    def generate_client_id(prefix: str) -> str:
        """
            this has to generate a unique id for the host.process.thread
            as on the same host there might be several processes using the provider
            and within the same process there might be several thread using the provider
        """
        host_id: int = uuid.getnode()
        proc_id: int = os.getpid()
        thrd_id: int = threading.current_thread().ident

        #   do not show your MAC
        if prefix == None:
            strkey: str = str(host_id) + str(proc_id) + str(thrd_id)
        else:
            strkey: str = prefix + str(host_id) + str(proc_id) + str(thrd_id)

        client_id: str = hashlib.md5(strkey.encode()).hexdigest()
        return client_id

    def on_publish(self, client, userdata, result):  # create function for callback
        #self._on_data("","data published \n")
        #logger.writeLog(LogSeverity.DEBUG, "data published")
        pass

    def _open(self) -> DopError:
        try: 
            #self.close()
            self._output_client.connect_async(self._host, port=self._port,
                    keepalive=self._keepalive, bind_address=self._bind_address)
            self._output_client.loop_start()
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()

            return DopError(99,"An exception occurred while connecting to the broker.")
        
        if self.wait_for_event_status(self._timeout, self._connection_event, True) == False:
            err: DopError = DopError(101,"Cannot connect to broker: timeout expired.")
            self._on_error(err)
            return err

        return DopError()       

    def open(self) -> DopError:
        if not self._configured:
            return DopError(2, "Provider cannot open: it is not yet configured.")
            
        self.close()
        #self._output_client = mqtt.Client()
        self._output_client = Client(self._client_id, clean_session= False, reconnect_on_failure = True)
        self._output_client.on_publish = self.on_publish
        self._output_client.on_connect = self.on_connect
        self._output_client.on_disconnect = self.on_disconnect

        err: DopError = DopError()
        while self.stopEvent.is_exiting() == False:    
            self._on_error(DopError(0,"Opening output mqtt provider retry count " + str(self._retries_count)))    
            err = self._open()
            if err.isError() == False:
                break

            self.set_lastError(err)
            if self._max_retries < self._retries_count:
                #   maximum number of retries has been exceeded
                err.rip()   #   this has tp be considered a non recoverable error
                self._on_error(err)
                return err
            self._retries_count += 1
            time.sleep(0.5)

        self._retries_count = 0   
        self._on_error(DopError(0,"output mqtt provider opened"))
        return DopError()


    def close(self) -> DopError:
        if self._connection_event.is_set():
            self._output_client.disconnect()
            
            #wait for disconnection
            self.wait_for_event_status(self._timeout, self._connection_event, False)
            self._output_client.loop_stop()

        self._on_error(DopError(0,"output mqtt provider closed"))
        return DopError()

    def write(self, msg: str, additional_info: dict = None) -> DopError:
        #   outputprovider
        #   the ._on_data is called after the data has been successfully written
       
        #self._on_data("", "Publishing event: " + msg)        
        try:
            err, res = self._output_client.publish(
                self._topic, msg, qos = self._qos)

            if err != 0:
                return DopError(201, "An error occurred while publishing a message.")
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()

            return DopError(202, "An exception occurred while publishing a message.")
		
        return DopError(0, "Event published")
   

    def writeEvent(self, msg: DopEvent, additional_info: dict = None) -> DopError:
        try: 
            payload = json.dumps(msg.to_dict())
            if msg.header.session: 
               
                err, res = self._output_client.publish(
                    topic = f'{self._topic}/{msg.header.session}', 
                    payload = payload, 
                    qos = self._qos)

                if err != 0:
                    return DopError(201, "An error occurred while publishing a message.")

        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()

            return DopError(202, "An exception occurred while publishing a message.")
        return DopError(0, "Event published")

    
    def write_to_endpoint(self, msg: str, subtopic, additional_info: dict = None) -> DopError:
        #   outputprovider
        #   the ._on_data is called after the data has been successfully written
       
        #self._on_data("", "Publishing event: " + msg)        
        try:
            err, res = self._output_client.publish(
                f"{self._topic}/{subtopic}", msg, qos = self._qos)

            if err != 0:
                return DopError(201, "An error occurred while publishing a message.")
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()

            return DopError(202, "An exception occurred while publishing a message.")
		
        return DopError(0, "Event published")