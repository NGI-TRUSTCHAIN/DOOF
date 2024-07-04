#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

import pika
from pika.exceptions import AMQPConnectionError

from threading import Event, Thread
import threading

from provider.python.presentation.input.provider_pres_input import inputPresentationProvider
from common.python.error import DopError
from common.python.utils import DopUtils
from common.python.threads import DopStopEvent


from inspect import currentframe, getframeinfo
import time
import traceback
import sys

class inputRabbitQueue(inputPresentationProvider):

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

        
        # ADDITIONAL CONFIGURABLE PARAMS
        self.passive = None
        self.durable = None
        self.exclusive = None
        self.auto_delete = None
        self.prefetch_count = None
        self.prefetch_size = None
        self.global_qos = None
        self.consumer_tag = None
        self._consumer_tag = None

        self._loop = Thread(target=self._inner_read, args=())
        # _innerStopEvent is needed in order to allow the provider 
        # to finish the inner loop (in another thread) when the close() 
        # method is invoked, independently from the globalStopEvent  
        self._innerStopEvent = DopStopEvent()

        super().__init__()

    
    def init(self, confstring: str) -> DopError:
        #   configuraion example
        #        input:
        #        provider: inputRabbitQueue
        #           parameters:
        #               url
        #               queue_name/queue/topic
        #               rc  retry counts (number of retries after recoverable error)
        #               rd  retry delay (number of seconds to wait before attempting the next retry)
        #               dm  delivery mode --> TODO is dm necessary for the input?
        #        configuration: url=amqp://guest:guest@127.0.0.1:5672/;queue_name=imperatives;rc=5;rd=10;dm=1;
      
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
            derr: DopError = DopError(1, 'Configuration missing mandatory parameter(s).')
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
        
        # ADDITIONAL CONFIGURABLE PARAMS
        if 'queue_passive' in self.config: 
            self.queue_passive = self.config['queue_passive']
        else: 
            self.queue_passive = False 

        if 'queue_durable' in self.config: 
            self.queue_durable = self.config['queue_durable']
        else: 
            self.queue_durable = True

        if 'queue_exclusive' in self.config: 
            self.queue_exclusive = self.config['queue_exclusive']
        else: 
            self.queue_exclusive = False 

        if 'queue_auto_delete' in self.config: 
            self.queue_auto_delete = self.config['queue_auto_delete']
        else: 
            self.queue_auto_delete = False 

        if 'qos_prefetch_count' in self.config:
            self.prefetch_count = self.config['qos_prefetch_count']
        else: 
            self.prefetch_count = 0 

        if 'qos_prefetch_size' in self.config:
            self.prefetch_size = self.config['qos_prefetch_size']
        else: 
            self.prefetch_size = 0 

        if 'global_qos' in self.config:
            self.global_qos = self.config['global_qos']
        else: 
            self.global_qos = False


        self._is_configured = True
        self._on_error(DopError(0,'Provider configured.'))
        return DopError()


    def __open(self) -> DopError:
        try:
            self.connection = pika.BlockingConnection(self.parameters)
            return DopError()
        except AMQPConnectionError as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()

            return DopError(101, 'AMQP connection error.')

    def open(self) -> DopError:
        
        self._on_error(DopError(0,'Opening.'))
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
                self.channel = self.connection.channel()
                self.channel.queue_declare(queue=self.queue, durable=self.queue_durable, 
                        exclusive=self.queue_exclusive, auto_delete=self.queue_auto_delete)

                #channel.confirm_delivery()  # TODO check: is it necessary for the recipient/consumer to confirm delivery?
                self._on_error(DopError(0, "Opened."))
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

    # CALLBACK
    def _on_message(self, channel, method, properties, body):
        # Process event 
        self._on_data("imperatives", body.decode())
        
        #If something happens in the on_data_fun and the program exists 
        # e.g. because of exception, the acknowledgement is not performed
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def _inner_read(self):
        
        #self.channel.basic_qos(
        #    prefetch_count=self.prefetch_count
        #)
        #try: 
        self._on_error(DopError(0, "Reading."))
        for message in self.channel.consume(self.queue, inactivity_timeout=1):
            if self.stopEvent.is_exiting() or self._innerStopEvent.is_exiting():
                self.channel.cancel()
                break
            if not message:
                continue
            method, properties, body = message

            #print(body)
            if body is not None:
                self._on_message(self.channel, method, properties, body)
        #except pika.exceptions.ConnectionClosed as e:
            #self.i_stop_event.stop()
        #    self.close()
        #    self.open() 

    def read(self) -> DopError:
        """ 
        Create a thread to read with _inner_read() 
        This is needed for consuming messages on another thread 
        with respect to the main one - otherwise the function that
        does not allow the main program to do anything else
        after calling input_provider.read()
        """
        err = DopError()
        if not self._is_open:
            err = self.open()
        if err.isError():
            return err 
        
        self._loop.start()
        return DopError()

    def run(self) -> DopError: 
        self._on_error(DopError(0, "Reading."))
        
        
        self.channel.basic_qos(
            prefetch_count=self.prefetch_count
        )
        self._consumer_tag = self.channel.basic_consume(
            queue=self.queue,
            consumer_callback=self._on_message,
            # auto_ack=True
        )
        

        self.channel.start_consuming()
        

    def close(self) -> DopError:
    
        if self._is_open == False:
            return DopError()

        self._is_open = False
        try:
            #self.channel.stop_consuming()
            self._innerStopEvent.stop()
            while True:
                if not(self._loop.is_alive()):
                    break
                self._loop.join(1)

            self.connection.close()
            
            self._on_error(DopError(0,"Closing."))
            return DopError()
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            
            err: DopError = DopError(150,"An exception occurred while closing AMQP connection.")
            self._on_error(err)
            return err
        