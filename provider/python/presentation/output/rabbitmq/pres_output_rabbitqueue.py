#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024


#   version:    1.0
#   date:       28/02/2024
#   author:     georgiana

import json
import pika
from pika.exceptions import AMQPConnectionError
import sys
import time


from provider.python.presentation.output.provider_pres_output import outputPresentationProvider
from common.python.error import DopError
from common.python.event import DopEvent
from common.python.utils import DopUtils


from inspect import currentframe, getframeinfo
import traceback


class outputRabbitQueue(outputPresentationProvider):

    def __init__(self):
        self.url = None
        self.queue = None
        self.parameters = None
        self.channel = None
        self.config = {}

        self._is_open: bool = False
        self._retries: int = 0
        self._retry_delay = 10              #   retry delay in seconds
        self._max_retries: int = 5          #   max number of retries
        self._is_configured: bool = False
        self._delivery_mode: int = 1        #   see AMQP/rabbit mq for delivery mode

        super().__init__()



    def init(self, confstring: str) -> DopError:

        #   configuraion parameters:
        #               url
        #               queue_name/queue/topic
        #               rc  retry counts (number of retries after recoverable error)
        #               rd  retry delay (number of seconds to wait before attempting the next retry)
        #               dm  delivery mode
        #   "configuration": "url=amqp://guest:guest@127.0.0.1:5672/;queue_name=imperatives;rc=5;rd=10;dm=1;"
      
        tupleConfig = DopUtils.config_to_dict(confstring)
        if tupleConfig[0].isError():
            return tupleConfig[0]
        self.config = tupleConfig[1]
        has_url: bool = 'url' in self.config
        has_queue_name: bool = 'queue_name' in self.config
        if has_url:
            self.url = self.config['url']
            self.parameters = pika.URLParameters(self.url)

        if has_queue_name:
            self.queue = self.config['queue_name']

        if (has_url and has_queue_name) == False:
            derr: DopError = DopError(1,'Configuration missing mandatory parameter(s).')
            derr.rip()
            self._on_error(derr)
            return derr

        #   optional parameters
        #   retries count
        if 'rc' in self.config:
            self._max_retries = int(self.config['rc'])
        #   delivery mode
        if 'dm' in self.config:
            self._delivery_mode = int(self.config['dm'])
        #   retry delay
        if 'rd' in self.config:
            self._retry_delay = int(self.config['rd'])
        

        self._is_configured = True
        self._on_error(DopError(0,'Provider configured.'))
        return DopError()


    def __open(self) -> DopError:
        try:
            self.connection = pika.BlockingConnection(self.parameters)
            return DopError()
        except AMQPConnectionError:
            return DopError(101, 'AMQP connection error')
        


    def open(self) -> DopError:
        self._on_error(DopError(0,'Opening'))
        if self._is_configured == False:
            derr = DopError(2,'Provider cannot open: it is not yet configured.')
            self._on_error(derr)
            return derr
        if self._is_open == True:
            #   the provider had been opened already, close it and repoen it
            #   NOTE:   as an alternative, the provider can be left open
            self.close()

        err: DopError = DopError()
        i_retries: int = 0
        while i_retries < self._max_retries:

            if self.stopEvent.is_exiting() == True:
                self.close()
                self._on_error(DopError(0,'Exit signaled.'))
                return DopError()

            err = self.__open()
            if err.isError() == False:
                self._is_open = True
                channel = self.connection.channel()
                channel.queue_declare(queue=self.queue, durable=True, exclusive=False, auto_delete=False)
                channel.confirm_delivery()
                return DopError()
            else:
                if err.isRecoverable() == True:
                    self._on_error(DopError(0,'Open retry.'))
                    #   the error is recoverable, so sleep fpr a while before trying reopening
                    time.sleep(self._retry_delay)
                    i_retries += 1
                else:
                    #   unrecoverable error
                    self._on_error(err)
                    return err
        #   loop exhausted
        #   clearly this cannot be recovered
        err = DopError(100,'Error in opening provider: max number of retries reached.')
        #   mark the error as non recoverable
        err.rip()
        self._on_error(err)
        return err

    def __write(self, msg: str) -> DopError:
        
        try:
            channel = self.connection.channel()    
            #   delivery_mode
            #   1 non persistent (not stored on disk)
            #   2 persistent (stored on disk)

            channel.basic_publish(
                exchange='',
                routing_key=self.queue,
                body=msg,
                properties=pika.BasicProperties(delivery_mode=self._delivery_mode)
            )

#            channel.basic_publish(
#                exchange='',
#                routing_key=self.queue,
#                body=msg,
#                properties=pika.BasicProperties(
#                    delivery_mode=1,
#                    mandatory=True
#                    )
#            )
            #   message has been published
            self._on_data("",msg)
            return DopError()
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            
            #   never return a non recoverable error
            err = DopError(202,'An exception occurred while publishing a message.')
            self._on_error(err)
            return err

    def write(self, msg: str, additional_info: dict= None) -> DopError:

        err: DopError = DopError()

        if self._is_open == False:
            err = self.open()
            if err.isError():
                self._on_error(err)
                return err
            #err = DopError(204,'Error: writing before opening provider.')
            #self._on_error(err)
            #return err

        
        i_retries: int = 0
        while i_retries <= self._max_retries:
            err = self.__write(msg)
            if err.isError() == False:
                #   write was successful
                return DopError()
            else:
                if err.isRecoverable() == True:
                    i_retries += 1
                    #   close the connection and reopen the connection
                    self.close()
                    err = self.open()
                    if err.isError():
                        self._on_error(err)
                        return err
                else:
                    #   unrecoverable error
                    self._on_error(err)
                    return err

        #   loop has exhausted
        err = DopError(203,'Write unrecoverable error')
        err.rip()
        self._on_error(err)
        return err
            
    def writeEvent(self, msg: DopEvent, additional_info: dict=None) -> DopError:
        
        err: DopError = DopError()

        if self._is_open == False:
            err = DopError(204,'Error: writing before opening provider.')
            self._on_error(err)
            return err

        
        i_retries: int = 0
        while i_retries <= self._max_retries:
            err = self.__write(json.dumps(msg.to_dict()))
            if err.isError() == False:
                #   write was successful
                return DopError()
            else:
                if err.isRecoverable() == True:
                    i_retries += 1
                    #   close the connection and reopen the connection
                    self.close()
                    err = self.open()
                    if err.isError():
                        self._on_error(err)
                        return err
                else:
                    #   unrecoverable error
                    self._on_error(err)
                    return err

        #   loop has exhausted
        err = DopError(203,'Write unrecoverable error')
        err.rip()
        self._on_error(err)
        return err
    
    def write_to_endpoint(self, msg, endpoint, additional_info: dict = None) -> DopError:
        
        return DopError(0, "not implemented")

    def close(self) -> DopError:
        if self._is_open == False:
            return DopError()

        self._is_open = False
        try:
            self.connection.close()
            self._on_error(DopError(0,'Closing.'))
            return DopError()
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            
            err: DopError = DopError(150,"An exception occurred while closing AMQP connection.")
            self._on_error(err)
            return err
            
        
        


