#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   version 2.0
#   03/05/2024
#   author : georgiana


#   version 2.0
#   - JSON configuration file syntax
#   - support for pipeline of processors  

import argparse
from distutils.log import Log
from inspect import currentframe, getframeinfo 
import json
from json import JSONDecodeError
from multiprocessing.dummy import Process
from platform import processor
import signal
import time
import traceback
from typing import Tuple
import sys 


from common.python.error import DopError, LogSeverity
from common.python.utils import DopUtils
from common.python.threads import DopStopEvent
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs

import load_processors_pipeline as lpp 

def get_args(argl = None):
    parser = argparse.ArgumentParser(description='Worker')
    parser.add_argument('-c',
                    '--config',
                    action="store",
                    required=False,
                    dest="config", help='path to config file')
    return parser.parse_args()
 


globalStopEvent = DopStopEvent()

def signalHandlerDefault(signalNumber, frame):
    print('Received:', signalNumber)

def progstop():
    print('Exiting ...')
    globalStopEvent.stop()

def signalHandlerExit(signalNumber, frame):
    #   set the exit event
    progstop() 

def signalManagement():
    signal.signal(signal.SIGTERM, signalHandlerExit)
    signal.signal(signal.SIGINT, signalHandlerExit)
    signal.signal(signal.SIGQUIT, signalHandlerExit)


class Worker:
    """ This is the userdata class assigned to the input provider
    for an asynchronous event processing  """
    def __init__(self): 
        # Declare providers and processors
        self._output = None
        self._database = None
        self._blockchain = None
        self._logger = None
        self._lookup_table = None 
        self._processor_envs = ProcessorEnvs() # or None

    @property 
    def output(self):
        return self._output

    @output.setter
    def output(self, output):
        self._output = output 

    @property 
    def database(self):
        return self._database

    @database.setter
    def database(self, database):
        self._database = database
       

    @property 
    def blockchain(self):
        return self._blockchain
    
    @blockchain.setter
    def blockchain(self, blockchain):
        self._blockchain = blockchain

    
    @property 
    def logger(self):
        return self._logger 
    
    @logger.setter
    def logger(self, logger):
        self._logger = logger
    
   
    @property 
    def lookup_table(self):
        return self._lookup_table

    @lookup_table.setter
    def lookup_table(self, lookup):
        self._lookup_table = lookup

    
    @property 
    def encryption_table(self):
        return self._encryption_table

    @encryption_table.setter
    def encryption_table(self, encryption):
        self._encryption_table = encryption

    @property 
    def integrity_provider(self):
        return self._integrity_provider 

    @integrity_provider.setter
    def integrity_provider(self, integrity):
        self._integrity_provider = integrity

    @property 
    def processor_envs(self):
        return self._processor_envs 

    @processor_envs.setter
    def processor_envs(self, processor_envs):
        self._processor_envs = processor_envs

    def tracefun(self, called: str):
        #print('\x1b[1;91m Worker [' + called + ']' + '\x1b[0m')
        # could be a call to the logger

        """"""

    def tracerr(self, err: DopError):
        #print('\x1b[1;91m err: ' + str(err.code) + ' msg: ' + err.msg + '\x1b[0m')
        # could be a call to the logger

        """"""
        print(err)

    def _eventify_err(self, input_event_header: DopEventHeader, err: DopError, params, werr = False):
        header = DopEventHeader(input_event_header.session,
                                input_event_header.task,
                                "error")
        w = err.code if werr == True else 0 
        e = err.code if werr == False else 0
        perr = 0 
        if err.perr is not None:
            perr = err.perr.code

        payload_dict = {
                "werr" : w, 
                "err" : e,  
                "perr" : perr,
                "msg": err.msg
            }
        payload_dict.update(params)
        
        return DopEvent(header, DopEventPayload(payload_dict))

    def _input_validation(self, event: str) -> Tuple[DopError, dict]:
        # This function validates that the input event is formatted correctly (json)
        # and contains the needed parameters ("session", "event")

        # The function returns a tuple containing: 
        # 1) a DopError
        # 2) a dictionary, which contains the contents of the event if the event is a valid JSON, 
        # otherwise is empty
        

        # PARSING
        try:
            body = json.loads(event)
        except JSONDecodeError:
            try:
                # msg coming from monitor
                body = json.loads(event.replace("'", '"'))
            except JSONDecodeError:
                # not returned to user, but logged
                # TODO go to logging?
                err = DopUtils.create_dop_error(DopUtils.ERR_JSON)
                err.notifiable = False
                return err, {} 
        
        # REQUIRMENTS VALIDATION
        session = body.get("session", None)
        if session is None:
            # not returned to user, but logged
            return DopUtils.create_dop_error(DopUtils.ERR_SESSION_REQ), body
    
        # the token contains only hex chars
        try:
            tmp_session = session.replace('-', '')
        except Exception as e:
            return DopUtils.create_dop_error(DopUtils.ERR_SESSION_FORMAT), body
        try:
            int(tmp_session, 16)
        except ValueError:
            err = DopUtils.create_dop_error(DopUtils.ERR_SESSION_HEX)
            err.notifiable = False 
            return err, body

        event_f = body.get("event", None)
        if event_f is None: 
            # TODO go to logging and notification
            err = DopUtils.create_dop_error(DopUtils.ERR_EVENT_REQ)
            err.notifiable = False
            return err, body 
        
        if event_f != DopEvent.LOGIN \
            and event_f != DopEvent.ENCRYPTION_LOGIN \
            and event_f != DopEvent.CIPHER_SUITE_QUERY \
            and event_f != "dop_log": 
            
            params = body.get("params", None)
            if params is None: 
                err = DopUtils.create_dop_error(DopUtils.ERR_PARAMS_REQUIRED)
                err.notifiable = False
                return err, body
         
            auth_token = params.get("auth_token", None)
            if auth_token is None: 
                err = DopUtils.create_dop_error(DopUtils.ERR_AUTHENTICATION_REQUIRED)
                err.notifiable = False
                return err, body
            
            # the token contains only hex characters 
            try:
                int(auth_token, 16)
            except ValueError:
                err = DopUtils.create_dop_error(DopUtils.ERR_TOKEN_HEX) 
                err.notifiable = False 
                return err, body


        return DopError(), body


    def _execute_main_pipeline(self, event: DopEvent, pipeline: list):
        
        self._processor_envs.empty_events_stack()
        self._processor_envs.empty_data_stack()
        
        self._logger.log(24604, LogSeverity.INFO, 
                            getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                            {"msg":"Event lookup OK.", "opt": f"handling event with {event.header.event} pipeline."})
 
        try: 
            #   before the processor is fired, the transaction is begun (2PC/XA compliant logic)
            #   against the external resource managers in a distributed transaction processing env
            self._database.begin_transaction()
            self._blockchain.begin_transaction()
            err = DopError()
            err_occurred = False
            #   the selected processor pipeline is fired against the incoming event: 
            #   processors are called in the order specified in configuration file for the given input event;
            for processor_handle in pipeline:
                
                # processors either handle the input event or events which were
                # placed by other processors in the stack data structure
        
                err =  processor_handle.handle_event(event, self._processor_envs)
                    
                if err.isError():
                    err_occurred = True
                    self._logger.log(f"Error returned by processor {processor_handle} for input event {event.header.event}", 
                                LogSeverity.ERROR, getframeinfo(currentframe()).filename, 
                                getframeinfo(currentframe()).lineno, err.to_dict())
                    
                    # worker empties the events stack and pushes the event-ified error on it 

                    break
            
                self._logger.log(24605, LogSeverity.DEBUG, 
                        getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno, 
                        {"msg": f"Processor {processor_handle} handled event.", "output": err.to_dict()})
                
            if err_occurred: 
                self._database.rollback()
                self._blockchain.rollback()
               
            else: 
                self._database.commit()
                self._blockchain.commit()

        except Exception as e: 
            self._database.rollback()
            self._blockchain.rollback()

            err = DopUtils.create_dop_error(DopUtils.ERR_REQ_PROCESSING)
            self._logger.log(err.code, LogSeverity.ERROR, 
                        getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                        {"msg": err.msg})
            
            print(f"""{int(time.time())} | {getframeinfo(currentframe()).filename} |
                    {getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}""", file = sys.stderr)
            sys.stderr.flush()
                    
        return err
    
    def _execute_finally_pipeline(self, pipeline):
        err = DopError()
        try:
            for processor_handle in pipeline:
            
                err = processor_handle.handle_pipeline_stack(self._processor_envs.pipeline_stack,
                                                self._processor_envs.providers)  
                
                self._logger.log(24605, LogSeverity.DEBUG, 
                        getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno, 
                        {"msg": f"Processor {processor_handle} handled event."})
                
        except Exception as e: 
                
            err = DopUtils.create_dop_error(DopUtils.ERR_REQ_PROCESSING)
            self._logger.log(err.code, LogSeverity.ERROR, 
                        getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                        {"msg": err.msg})
            
            print(f"""{int(time.time())} | {getframeinfo(currentframe()).filename} |
                    {getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}""", file = sys.stderr)
            sys.stderr.flush()
                    
        return err


    def _notification(self, event: DopEvent):
        
        for session in self._processor_envs.events.properties():
            for out_event in self._processor_envs.events.pop(session):
                try:
                    event_str = json.dumps(out_event.to_dict())
                except AttributeError as e:
                    event_str = json.dumps(out_event)

                self._logger.log(24606, LogSeverity.DEBUG, 
                    getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                    {"msg": "New DMP event to be sent to client.", 
                    #"event": out_event.to_dict()})
                    "session": session,
                    "event": event_str})
                #   the event is propagated to the output provider
                
                err = self._output.write_to_endpoint(event_str, session)
                if err.isError():
                    self._logger.log(f"Error in writing event to output", LogSeverity.ERROR, 
                                     getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno, err.to_dict())
    
    def handlemsg(self, event: str):

        if self._output is None: 
            return 
        
        try:
            err, in_event_dict = self._input_validation(event) 
        except Exception as e: 
            self._logger.log("An exception occurred in validating input", LogSeverity.ERROR, 
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                {"input_event" : event})  
            return
            

        if err.isError():
            
            self._logger.log(int(f"24{err.code}") , LogSeverity.DEBUG, 
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                {"msg": err.msg, "input_event" : in_event_dict})  
            
            """
            # TODO checks: is any of the replies from input_validation notifiable?
            """
        else: 
            in_event_header = DopEventHeader(
                                in_event_dict.get('session'),
                                in_event_dict.get('task', None),
                                in_event_dict.get('event'))
            
            in_event = DopEvent(in_event_header,
                                DopEventPayload(in_event_dict.get('params',{})))
            
            # in_event = eventified input event
            self._logger.log(24601, LogSeverity.DEBUG,
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno, 
                {"msg":"A new event was received.", "event": in_event.to_dict()})
                
            # pipeline selection
            pipeline = self.lookup_table.get(in_event_header.event, None)

            if pipeline is None: 
                # No pipeline found
                err = DopUtils.create_dop_error(DopUtils.ERR_UNRECOGNIZED_EVENT)
                err.notifiable = False
                self._logger.log(int(f"24{err.code}") , LogSeverity.DEBUG, 
                    getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                    {"msg": err.msg}) 
                
                if err.notifiable: 
                    # TODO check if this is ok here
                    err_event = self._eventify_err(in_event_header, err,
                                    {"input_event" : in_event_header.event}, werr= True)
                    self._processor_envs.events.push(err_event.header.session, err_event)
                    # notification at the end

            else:
                pipeline_main = pipeline.get('main', [])
                pipeline_finally = pipeline.get('finally', [])

                # MLE-MULTISESSION-MACRO: lookup happens in pipeline
                err = self._execute_main_pipeline(in_event, pipeline_main)
                if err.isError():
                    self._processor_envs.empty_events_stack()
                    
                    if err.notifiable:
                        out_event = self._eventify_err(in_event_header, err, {"input_event" : in_event_header.event})    
                        self._processor_envs.events.push(out_event.header.event, out_event)
                
                # finally pipeline: there is a finally for each event pipeline;
                err = self._execute_finally_pipeline(pipeline_finally)
                if err.isError(): 
                    # TODO CHECK What happens if there is an error in this step? do we need a finally 
                    # for the finally which we know for sure that can return no error? 
                    self._processor_envs.empty_events_stack()
                    if err.notifiable:
                        out_event = self._eventify_err(in_event_header, err, {"input_event" : in_event_header.event})    
                        #delete session from out_event header

                        self._processor_envs.events.push(out_event.header.session, out_event)
                # notification at the end
        
        self._notification(in_event_dict)
                


globalWorkerIN = Worker()


def in_error_callback(err: DopError, userdata):
    worker: Worker = userdata
    worker.tracefun('in_error_callback')
    worker.tracerr(err)

    #   the following is just a suggestion about how to react to non recoverable errors
    if err.isRecoverable()==False:
        globalStopEvent.stop()
    return

def in_data_callback(message_topic: str, message_payload: str, userdata):

    #   example: how to use userdata
    worker: Worker = userdata
    worker.tracefun('in_data_callback')

    worker.handlemsg(message_payload)
    
    return


def out_error_callback(err: DopError, userdata):
    if err.isError():
        print('\x1b[1;33m' + 'err: ' + str(err.code) + ' msg: ' + err.msg + '\x1b[0m')
    else:
        print('\x1b[1;33m' +  'log: ' + err.msg+ '\x1b[0m')


def check_providers_in_conf(configuration_dict) -> DopError:
    # CHECKS
    conf_list = ['inputProvider', 'outputProvider', 'databaseProvider', # TODO persistenceProvider
            'intermediationWorkerProvider', 'pipelines', 'loggingProvider', 
            'integrityProvider', 'cryptoProviders',
            'encodingProvider']

    errs = {"inputProvider":110,"outputProvider":111,
        "integrityProvider":112,"encodingProvider":113,
        "databaseProvider":114,"intermediationWorkerProvider":115, #TODO persistence 
        "processors":116,"loggingProvider":117,
        "cryptoProviders":118
    }

    for item in conf_list: 
        if item not in configuration_dict:
            
            return DopError(int(f"24{errs[item]}"), f"Configuration value error: {item} key \
                is undefined/missing.")
    
    return DopError()



def main(confFilePath, args, open_providers) -> DopError:

    # GET CONFIGURATION

    
    configuration_dict = {}

    try: 
        with open(confFilePath) as conf:
            configuration_dict: dict = json.loads(conf.read())
    except Exception as e :
        print(e)
        return DopError(24102,"Error in parsing the configuration file")
    
    err: DopError = check_providers_in_conf(configuration_dict)
    
    if err.isError():
        print(err.msg) # missing {item} from conf file 
        return err 


    # Before loading anything, check that MACROS are
    # syntactically OK (no circular dependencies)

    macros: dict = configuration_dict['macros']
    valid = lpp.macros_are_valid(macros)

    if not valid: 
        return DopError(199, "Invalid macros for pipeline. Please check that there is no circular dependency.")
    
    
    input_configuration: dict = configuration_dict['inputProvider']
    output_configuration: dict = configuration_dict['outputProvider']

    db_configuration: dict = configuration_dict['databaseProvider']
    blk_configuration: dict = configuration_dict['blockchainWorkerProvider']

    logger_configuration: dict = configuration_dict['loggingProvider']

    cryptos_configuration: dict = configuration_dict['cryptoProviders']
    integrity_configuration: dict = configuration_dict['integrityProvider']
    encoding_configuration: dict = configuration_dict['encodingProvider']

    # processors (take the whole array of processor configurations) 
    processors_configuration: dict = configuration_dict['pipelines']

    
    # LOGGING
    tupleLoadProvider = DopUtils.load_provider(logger_configuration)
    if tupleLoadProvider[0].isError():
        error = DopError(24211, "Error in loading Logger provider")
        error.perr=tupleLoadProvider[0]
        return error
    
    logger_provider = tupleLoadProvider[1]
    logger_provider.attach_stop_event(globalStopEvent)          # globalStop

    logger_connstring: str = logger_configuration['configuration']
    per: DopError = logger_provider.init(logger_connstring)
    if per.isError():
        error = DopError(24212,"Error in initializing Logger provider.")
        error.perr = per
        return error
        
    per: DopError = logger_provider.open()
    if per.isError():
        error = DopError(24304,"Error in opening Logger provider.")
        error.perr = per
        return error

    open_providers.append(logger_provider)


    globalWorkerIN.logger = logger_provider 


    #   loading outputProvider
    tupleLoadProvider = DopUtils.load_provider(output_configuration)
    if tupleLoadProvider[0].isError():
        error = DopError(24202, "Error in loading the output provider.")
        error.perr = tupleLoadProvider[0]
        logger_provider.log(error.code, LogSeverity.CRITICAL, 
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno, 
                {'msg': error.msg, 'per': error.perr.to_dict()}) 
        return error
    output_provider = tupleLoadProvider[1]
    

    output_confstring: str = output_configuration['configuration']
    per: DopError = output_provider.init(output_confstring)
    if per.isError():
        error = DopError(24204,"Error in initializing the output provider.")
        error.perr = per
        logger_provider.log(error.code, LogSeverity.CRITICAL,
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,    
                {'msg': error.msg, 'per': error.perr.to_dict()})
        return error
    

    #   loading input provider
    tupleLoadProvider = DopUtils.load_provider(input_configuration)
    if tupleLoadProvider[0].isError():
        error = DopError(24201,"Error in loading the input provider.")
        error.perr=tupleLoadProvider[0]
        logger_provider.log(error.code, LogSeverity.CRITICAL,
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                {'msg': error.msg, 'per': error.perr.to_dict()}) 
        return error
    input_provider = tupleLoadProvider[1]

    input_confstring: str = input_configuration['configuration']
    per: DopError = input_provider.init(input_confstring)
    if per.isError():
        error = DopError(24203,"Error in initializing the input provider.")
        error.perr = per
        logger_provider.log(error.code, LogSeverity.CRITICAL,\
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                {'msg':error.msg, 'per': error.perr.to_dict()}) 
        
        return error

    #   loading db provider
    tupleLoadProvider = DopUtils.load_provider(db_configuration)
    if tupleLoadProvider[0].isError(): #tupleLoadProvider[0].msg
        error = DopError(24205,"Error in loading the persistence provider.")
        logger_provider.log(error.code, LogSeverity.CRITICAL,
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno, 
                {'msg':error.msg, 'cause':tupleLoadProvider[0].to_dict()})
        return tupleLoadProvider[0]
    db_provider = tupleLoadProvider[1]

    db_confstring: str = db_configuration['configuration']
    per: DopError = db_provider.init(db_confstring)
    if per.isError():  
        error = DopError(24206,"Error in initializing the persistence provider.")
        error.perr = per
        logger_provider.log(error.code, LogSeverity.CRITICAL,
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                {'msg': error.msg, 'per': per.to_dict()})
        
        return error
    
     # loading blk provider
    tupleLoadProvider = DopUtils.load_provider(blk_configuration)
    if tupleLoadProvider[0].isError():
        error = DopError(24209,"Error in loading the blockchain provider.") 
        logger_provider.log(error.code, LogSeverity.CRITICAL,
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno, 
                {'msg': error.msg, 'cause': tupleLoadProvider[0].to_dict()})
        
        return tupleLoadProvider[0]
    blk_provider = tupleLoadProvider[1]

    blk_confstring: str = blk_configuration['configuration']
    per: DopError = blk_provider.init(blk_confstring)
    if per.isError():  
        error = DopError(24210,"Error in initializing the blockchain provider.")
        error.perr = per
        logger_provider.log(error.code, LogSeverity.CRITICAL,
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno, 
                {'msg': error.msg, 'per': error.perr.to_dict()})
        
        return error




    #   Loading MACROS
    loaded_macros = {}
    lpp.load_macros(macros, loaded_macros)

    for key, value in loaded_macros.items():
        print(f"{key}: {value}")

    #   loading PROCESSORS providers
    pipeline = lpp.load_processors(processors_configuration, loaded_macros)

    
    # loading crypto providers
    cryptos = {}
    for name, conf in cryptos_configuration.items():
        
        tupleLoadProv = DopUtils.load_provider(conf)
        if tupleLoadProv[0].isError(): 
            error = DopError(24213,f"Error in loading the encryption provider.")
            logger_provider.log(err.msg , LogSeverity.CRITICAL,
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno, 
                {'msg': error.msg, 'cause': tupleLoadProvider[0].to_dict(), 'provider': name})
            
            return tupleLoadProv[0]
        crypto_provider = tupleLoadProv[1]

        cp_confstring: str = conf['configuration']
        per: DopError = crypto_provider.init(cp_confstring)
        if per.isError(): 
            error = DopError(24214,"Error in initializing the encryption provider." )
            error.perr = per
            logger_provider.log(error.code, LogSeverity.CRITICAL,
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno, 
                {'msg':error.msg, 'per':per.to_dict(), 'provider': name})
            
            return error

        crypto_provider.attach_stop_event(globalStopEvent)
        per = crypto_provider.open() 
        if per.isError(): 
            error = DopError(24308, "Error in opening the encryption provider.")
            error.perr = per
            logger_provider.log(error.code, LogSeverity.CRITICAL,\
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                {'msg':error.msg, 'per':per.to_dict(), 'provider': name})
            
            return error
        open_providers.append(crypto_provider)

        cryptos[name.lower()] = crypto_provider


    #   loading integrity provider
    tupleLoadProvider = DopUtils.load_provider(integrity_configuration)
    if tupleLoadProvider[0].isError():
        error = DopError(24207,"Error in loading the integrity provider.")
        logger_provider.log(error.code, LogSeverity.CRITICAL,
                getframeinfo(currentframe()).filename,
                getframeinfo(currentframe()).lineno,
                {'msg': error.msg,'cause':tupleLoadProvider[0].to_dict()})
            
        return tupleLoadProvider[0]
    integrity_provider = tupleLoadProvider[1]
    
    """
    integrity_confstring: str = integrity_configuration['configuration']
    err: DopError = integrity_provider.init(integrity_confstring)
    if err.isError():
        return err
    """

    
    #   loading encoding provider
    tupleLoadProvider = DopUtils.load_provider(encoding_configuration)
    if tupleLoadProvider[0].isError(): 
        error = DopError(24208,"Error in loading the encoding provider.")
        logger_provider.log(error.code, LogSeverity.CRITICAL,
                getframeinfo(currentframe()).filename, 
                getframeinfo(currentframe()).lineno,
                {'msg':error.msg, 'cause':tupleLoadProvider[0].to_dict()})
        
        return tupleLoadProvider[0]
    encoding_provider = tupleLoadProvider[1]
    


    # Set callbacks/userdata/stop events
    
    #on_data_callback 
    #on_error_callback
    #userdata 

    output_provider.attach_stop_event(globalStopEvent)          # globalStop
    output_provider.set_on_error_callback(out_error_callback)

    input_provider.attach_stop_event(globalStopEvent)
    input_provider.set_on_data_callback(in_data_callback)
    input_provider.set_on_error_callback(in_error_callback)  
    input_provider.set_userdata(globalWorkerIN)
    
    
    db_provider.attach_stop_event(globalStopEvent)

    blk_provider.attach_stop_event(globalStopEvent)


    
    # SET WORKER VARIABLES
    globalWorkerIN.output = output_provider
    globalWorkerIN.database = db_provider 
    globalWorkerIN.blockchain = blk_provider
    globalWorkerIN.lookup_table = pipeline

    proc_envs = ProcessorEnvs()
    proc_envs.db_provider = db_provider
    proc_envs.blk_provider = blk_provider
    proc_envs.integrity_provider = integrity_provider
    proc_envs.encoding_provider = encoding_provider 
    proc_envs.crypto_providers = cryptos
    proc_envs.logger_provider = logger_provider
    globalWorkerIN.processor_envs = proc_envs
   

    # open providers

    # processors (in case they need to open other modules etc ...)
    for event, pipelines in pipeline.items():
        for top, procs in pipelines.items():
            for proc in procs: 
                per: DopError = proc.open()
                if per.isError(): 
                    error = DopError(24307,"Error in opening processor.")
                    error.perr = per
                    logger_provider.log(error.code, LogSeverity.CRITICAL,
                        getframeinfo(currentframe()).filename, 
                        getframeinfo(currentframe()).lineno,
                        {'msg':error.msg, 'per': error.perr.to_dict(), 'processor': event})
            
                    return err
                open_providers.append(proc)

    per: DopError = output_provider.open()
    if per.isError(): 
        error = DopError(14301,"Error in opening the output provider.")
        error.perr = per
        logger_provider.log(error.code, LogSeverity.CRITICAL,
                getframeinfo(currentframe()).filename,
                getframeinfo(currentframe()).lineno,
                {'msg': error.msg, 'per': per.to_dict()})
       
        return error
    open_providers.append(output_provider)

    try: 
        per: DopError = input_provider.open()
    
        if per.isError(): 
            error = DopError(24302,"Error in opening the input provider.")
            error.perr = per
            logger_provider.log(error.msg, LogSeverity.CRITICAL,
                    getframeinfo(currentframe()).filename, 
                    getframeinfo(currentframe()).lineno,
                    {'msg':error.msg, 'per': per.to_dict()})
        
            return error
        open_providers.append(input_provider)
    except OSError as e:
        print(f"""{int(time.time())} | {getframeinfo(currentframe()).filename} | 
             {getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}""", file = sys.stderr)
        sys.stderr.flush()
        return DopError(24302,"Error in opening the input provider.")


    per: DopError = db_provider.open()
    if per.isError(): 
        error = DopError(24305, "Error in opening the persistence .")
        error.perr = per
        logger_provider.log(error.code, LogSeverity.CRITICAL,\
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno, 
                {'msg': error.msg, 'per': per.to_dict()})
       
        return error
    open_providers.append(db_provider)

    
    per: DopError = blk_provider.open()
    if per.isError(): 
        error = DopError(24306, "Error in opening the blockchain provider.")
        error.perr = per
        logger_provider.log(error.code, LogSeverity.CRITICAL,
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                {'msg': error.msg, 'per': per.to_dict()})
       
        return error
    open_providers.append(blk_provider)
    
    ### LOOP ###

    input_provider.read()

    
    while True:
        if globalStopEvent.is_exiting():
            break
        globalStopEvent.wait(10)       #   do not waste too time within this wait - this is in seconds
        #time.sleep(10)

    ### EXIT ###

    #print("closing")

    logger_provider.log(24550, LogSeverity.INFO,\
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno, 
                {'msg':"Closing input provider"})
    per: DopError = input_provider.close()
    if per.isError(): 
        error = DopError(24501,"Error in closing the input provider.")
        error.perr = per
        logger_provider.log(error.code, LogSeverity.CRITICAL,\
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno, 
                {'msg': error.msg, 'per': per.to_dict()})
        return error

    logger_provider.log(24551, LogSeverity.DEBUG,\
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                {'msg': "Closing output provider."})
    per: DopError = output_provider.close()
    if per.isError(): 
        error = DopError(24502,"Error in closing the output provider.")
        error.perr = per
        logger_provider.log(error.code, LogSeverity.CRITICAL,\
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno, 
                {'msg': error.msg, 'per': per.to_dict()})       
        return error

    for event in pipeline:
        for proc in pipeline[event]['main']:
            logger_provider.log(24554, LogSeverity.INFO,\
                    getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                    {'msg': "Closing processor."})
            
            per: DopError = proc.close()
            if per.isError(): 
                error = DopError(24504, "Error in closing processor.")
                error.perr = per
                logger_provider.log(error.code, LogSeverity.CRITICAL,\
                    getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno, 
                    {'msg': error.msg, 'per': per.to_dict()})
                return error
        for proc in pipeline[event]['finally']:
            logger_provider.log(24554, LogSeverity.INFO,\
                    getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                    {'msg': "Closing processor."})
            
            per: DopError = proc.close()
            if per.isError(): 
                error = DopError(24504, "Error in closing processor.")
                error.perr = per
                logger_provider.log(error.code, LogSeverity.CRITICAL,\
                    getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno, 
                    {'msg': error.msg, 'per': per.to_dict()})
                return error

    logger_provider.log(24555, LogSeverity.INFO,\
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                {'msg': "Closing persistence provider."})
    per: DopError = db_provider.close()
    if per.isError():
        error = DopError(24503,"Error in closing the persistence provider.")
        error.perr = per
        logger_provider.log(error.code, LogSeverity.CRITICAL,\
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                {'msg': error.msg, 'per': per.to_dict()})
           
        return error
    # blk_provider.close


    logger_provider.close()

    return DopError()

    
if __name__ == "__main__":
    signalManagement()
    
    args = get_args()
    if args.config:
        config_file = args.config
    else: 
        config_file = ""
    print(config_file)
    providers_to_stop = []
    error:DopError = main(config_file,[], providers_to_stop)
    
    
    globalStopEvent.stop()
    for provider in reversed(providers_to_stop):
        provider.close()

    if error.isError():
        print(f"Exit - {error}") # already logged

