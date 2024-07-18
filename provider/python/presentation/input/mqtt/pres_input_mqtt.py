#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

import hashlib
import os
import sys
import time
import threading
import uuid


import paho.mqtt.client as mqtt
from threading import Event, Thread


from provider.python.presentation.input.provider_pres_input import inputPresentationProvider
from common.python.error import DopError
from common.python.utils import DopUtils

from inspect import currentframe, getframeinfo
import traceback


#   TODO
#   see error 101 subscription failure
#       luckily enough we could F see this event
#       =>  extend the logic so even this error is recoverable (reset F everything)

class inputMqttPaho(inputPresentationProvider):

    def __init__(self):
        self._client = None
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
        self._subscription_event: Event = Event()
        self._connection_event.clear()
        self._subscription_event.clear()

        self._is_closed = False
        super().__init__()

    def init(self,connstring: str) -> DopError:
        #   add parsing etc. now using default values
        
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
        return DopError()

    #=========================================================
    #       callbacks
    #=========================================================
    def on_connect(self, client, userdata, flags, rc):
        self._on_error(DopError(0,"connected with result code "+str(rc)))
        if rc != 0:
            #   failure connecting
            #   will the loop connect again ?
            self._on_error(DopError(100,"Could not connect to the broker."))
            if self.stopEvent.is_exiting() == False:
                if self._max_retries > self._retries_count:
                    self._retries_count += 1
                    self.open()
            return

        #   signal connection and trigger subscription
        self._connection_event.set()      
        err, self._last_mid = self._client.subscribe(self._topic, qos=self._qos)
        if err!=0:
            self._on_error(DopError(102,"Error in the subscription to the specified topic."))
            self._client.disconnect()  
            

    def on_disconnect(self, client, userdata, rc):
        #self._connection_event.clear()
        self.wait_for_event_status(self._timeout, self._connection_event, False)
        if rc != 0:
            self._on_error(DopError(103,"Unexpected disconnection."))

        if self.stopEvent.is_exiting() == False:
            #   no higher level exit has been signalled
            #   ==> try to reconnect
            #time.sleep(0.2)
            #self.open()
            self._is_closed = False
            self._client.reconnect()
        else: 
            self._is_closed = True

    def on_subscribe(self, client, userdata, mid, granted_qos):
        if mid == self._last_mid:
            self._subscription_event.set()
            return 
        self._on_error(DopError(104,"Subscription error."))

    def on_unsubscribe(self, client, userdata, mid):
        if mid == self._last_mid:
            self._subscribe_event.clear()        
            return
        self._on_error(DopError(105,"Unsubscription error."))
        

    def on_message(self, client, userdata, message):
        #   available message properties:
        #   message.qos
        #   message.topic
        #   message.payload
        #   only the message topic and the message payload will be propagated
        #   to the upper layer. see inputPresentationProvider._on_data method
        self._on_data(str(message.topic), str(message.payload.decode("utf-8")))



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

    def _open(self) -> DopError:
        
        #try:
        #    self.close()
        #except RuntimeError as e:
        #    print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
        #            f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
        #    sys.stderr.flush()
        

        try:
            self._client.connect_async(self._host,port=self._port,keepalive=self._keepalive, bind_address=self._bind_address)
            self._client.loop_start()
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
        if self._configured == False:
            return DopError(2,"Provider cannot open: it is not yet configured.")

        #   no matter if a client was allocated already, the previous instance
        #   is garbaged and a new instance is created - the reinitialise() method 
        #   does not seem to work, based on quite thorough testing
        self._client = mqtt.Client(self._client_id, clean_session= False, reconnect_on_failure = True)

        #   setup callbacks
        self._client.on_connect = self.on_connect
        self._client.on_disconnect = self.on_disconnect
        self._client.on_subscribe = self.on_subscribe
        self._client.on_unsubscribe = self.on_unsubscribe
        self._client.on_message = self.on_message

        err: DopError = DopError()
        while self.stopEvent.is_exiting() == False:    
            self._on_error(DopError(0,"opening provider retry count " + str(self._retries_count)))    
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
        return DopError()

    def read(self) -> DopError:
        return DopError()

    def close(self) -> DopError:
        if self._connection_event.is_set():
            self._client.disconnect()

            #   wait for disconnection

            if self.wait_for_event_status(self._timeout, self._connection_event, False) == False: 
                err: DopError = DopError(101,"Cannot disconnect from broker: timeout expired.")

            self._client.loop_stop()

        return DopError()

        
