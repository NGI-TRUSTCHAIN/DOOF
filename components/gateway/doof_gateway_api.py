#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   version:    1.0
#   date:       06/05/2024
#   author:     georgiana


import argparse
from flask import Flask, request, make_response, jsonify 
from flask_cors import CORS, cross_origin
import json
from inspect import currentframe, getframeinfo

import time
import threading, queue
from typing import Tuple 
import uwsgi

from common.python.error import DopError, LogSeverity
from common.python.utils import DopUtils
from common.python.threads import DopStopEvent
from provider.python.provider import Provider
from provider.python.presentation.output.provider_pres_output import outputPresentationProvider



#parser = argparse.ArgumentParser(description="Web application server for the DOP marketplace")
#parser.add_argument("-c","--conf", help = "The configuration file for the provider.", required = True)

#args = parser.parse_args()
#conf_file = args.conf

conf_file = uwsgi.opt['conf']
#conf_file = "./conf/rabbit_output.conf"

#############################

app = Flask(__name__)
CORS(app)

globalStopEvent = DopStopEvent()
providers_to_stop = queue.LifoQueue()

def teardown():
    print("Exit ...")
    globalStopEvent.stop()
    """
    while not providers_to_stop.empty():
        print("provider")
        provider = providers_to_stop.get_nowait()
        uwsgi.lock()
        provider.close()
        uwsgi.unlock()
    """



uwsgi.atexit = teardown


#############################

def load_provider(confFilePath, provider: str) -> Tuple[DopError, Provider]: 
    """
    This function needs to be called when a thread first instantiates
    its output provider. It loads the provider, and returns a reference 
    to it. 
    # type is output, logger etc
    """
    # read configuration
    #print("Reading configuration.")
    providerErrors = {
        "Configuration value error; outputProvider key is undefined/missing.":111,
        "Configuration value error; loggingProvider key is undefined/missing.":117,
        "Error in loading the output provider.":202, 
        "Error in initializing the output provider.": 204,
        "Error in loading the logger provider.":211,
        "Error in initializing the logger provider.":212,
        "Error in opening the output provider.": 301,
        "Error in opening the logger provider.":304,
    }
    tupleConfiguration = DopUtils.parse_yaml_configuration(confFilePath)
    if tupleConfiguration[0].isError():
        error = DopError(22102, "Error in parsing the configuration file.")
        return (error, None)

    configuration_dict: dict = tupleConfiguration[1]
    if (f'{provider}Provider' in configuration_dict) == False:
        msg = f"Configuration value error; {provider}Provider key is undefined/missing."
        error = DopError(int(f"22{providerErrors.get(msg)}"), msg)
        return (error, None)

    configuration: dict = configuration_dict[f'{provider}Provider']

    # load provider 
    #print("Loading provider.")
    tupleLoadProvider = DopUtils.load_provider(configuration)
    if tupleLoadProvider[0].isError():
        msg = f"Error in loading the {provider} provider."
        error = DopError(int(f"22{providerErrors.get(msg)}"),msg)
        return (error, None) 
    
    provider_obj = tupleLoadProvider[1]
    
    # initialize 
    confstring: str = configuration['configuration']
    per: DopError = provider_obj.init(confstring)
    if per.isError(): 
        msg = f"Error in initializing the {provider} provider."
        error = DopError(int(f"22{providerErrors.get(msg)}"),msg)
        error.perr = per
        return (error, None)
    
    # open 
    per = provider_obj.open()
    if per.isError():
        msg = f"Error in opening the {provider} provider."
        error = DopError(int(f"22{providerErrors.get(msg)}"),msg)
        error.perr = per
        return (error, None)

    return (DopError(), provider_obj)

#############################

class Provider_Array:
    def __init__(self):
        self._out_providers: dict = {}

    def _get(self, key) -> Tuple[int, str, outputPresentationProvider]:
        if key in self._out_providers:
            return (22780,"Using an already allocated provider.", self._out_providers[key])
        err, new_provider = load_provider(conf_file, 'output') # outputPresentationProvider
        if err.isError():
            return (err.code, err.msg, None)
       
        new_provider.attach_stop_event(globalStopEvent)
        providers_to_stop.put(new_provider)

        optMsg = f"New provider allocated for thread {key}."
        self._out_providers.update({key : new_provider})
        return (0, optMsg, self._out_providers[key])

    def get(self, key) -> Tuple[int, str, outputPresentationProvider]:
        uwsgi.lock()
        provTuple = self._get(key)
        uwsgi.unlock()
        return provTuple

PROVIDERS = Provider_Array()

############################
err, logger = load_provider(conf_file, 'logging')
if err.isError():
    print(f"{err.code} {err.msg}")
logger.attach_stop_event(globalStopEvent)
providers_to_stop.put(logger)
tid = threading.current_thread().ident
logger.log(22353, LogSeverity.INFO,
    getframeinfo(currentframe()).filename,
    getframeinfo(currentframe()).lineno,
    {"msg": "Logger Provider successfully opened.", "tid":tid})

############################
@app.route('/')
@app.route('/index')
@cross_origin()
def first_page():
    root = {"root": "/imperatives"}
    return make_response(jsonify(root))


@app.route('/imperatives', methods = ['POST'])
@cross_origin(allow_headers=['Content-Type', 'Access-Control-Allow-Origin'])
def accept_mess():
    
    logger.log(22601, LogSeverity.INFO, 
        getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
        {"msg":"A new message was received."})
    
    resp = {}
    
    json_check, err_resp = _json_check(request)
    if not json_check:
        return make_response(jsonify(err_resp), 400)
    
    ### HEADER OK ###
    try:
        mess = request.get_json()
        
    except Exception as e:
        ### CONTENT IS NOT JSON ### 
        logger.log(22704, LogSeverity.ERROR, 
            getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
            {"msg": str(e)})
        
        err_resp = {"err": 2}
        return make_response(jsonify(err_resp), 400)
    

    ### MESSAGE OK ###
    logger.log(22600, LogSeverity.DEBUG,
        getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
        mess)
    
    # get output provider 
    tid = threading.current_thread().ident
    err, msg, provider = PROVIDERS.get(tid)
    
    ### CHECK PROVIDER ### 
    prov_check, err_resp = _provider_check(msg, provider)
    if not prov_check:
        return make_response(jsonify(err_resp), 500)

    
    ### PROVIDER OK, WRITE MESSAGE ###
   
    written, resp = _write_mess(provider, json.dumps(mess))
    if not written:
        return make_response(jsonify(resp)), 500
    else:
        return make_response(jsonify(resp)), 200




@app.route('/getsession', methods = ['GET'])
@cross_origin()
def get_session_uuid():
    uuid = DopUtils.create_uuid()
    session = {
        'session' : uuid
    }
    resp = make_response(jsonify(session))
    return resp


@app.route('/sysadmin', methods = ['POST'])
@cross_origin(allow_headers=['Content-Type', 'Access-Control-Allow-Origin'])
def sysadmin():
    
    logger.log(22601, LogSeverity.INFO, 
        getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
        {"msg":"A new message from sysadmin was received."})
    
    json_check, err_resp = _json_check(request)
    if not json_check:
        return make_response(jsonify(err_resp), 400)
    
    ### JSON HEADER OK ###
    try:
        mess = request.get_json()
    except Exception as e:
        print(e)
        ### CONTENT IS NOT CORRECTLY FORMATTED ### 
        logger.log(22704, LogSeverity.ERROR,
            getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
            {"msg": str(e)})
        
        err_resp = {"err": 2}

        return make_response(jsonify(err_resp), 400)
    
    
        
    ### MESSAGE CONTENT OK, CHECK PROVIDER ###
    logger.log(22600, LogSeverity.DEBUG,
        getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
        mess)
    # get output provider
    tid = threading.current_thread().ident
    err, msg, provider = PROVIDERS.get(tid)
    prov_check, err_resp = _provider_check(msg, provider)
    if not prov_check:
        return make_response(jsonify(err_resp), 500)
    
    
    ### PROVIDER OK, WRITE MESSAGE  ### 
    
    written, resp = _write_mess(provider, json.dumps(mess))
    if not written:
        return make_response(jsonify(resp)), 500
    else:
        return make_response(jsonify(resp)), 200
    


@app.route('/startsession', methods = ['POST'])
@cross_origin(allow_headers=['Content-Type', 'Access-Control-Allow-Origin'])
def start_session():

    json_check, err_resp = _json_check(request)
    if not json_check:
        return make_response(jsonify(err_resp), 400)
    
    ### JSON HEADER OK ###
    try:
        mess = request.get_json()
        print(mess)
        subject = mess['sub']
        logger.log(0, LogSeverity.INFO, 
            getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
            {"msg": f"Received /startsession for subject: {subject}"})
    except Exception as e:
        print(e)
        ### CONTENT IS NOT CORRECTLY FORMATTED ### 
        logger.log(22704, LogSeverity.ERROR,
            getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
            {"msg": str(e)})
        
        err_resp = {"err": 2}
        return make_response(jsonify(err_resp), 400)
    
    ### MESSAGE CONTENT OK, CHECK PROVIDER ###
    
    # get output provider
    tid = threading.current_thread().ident
    err, msg, provider = PROVIDERS.get(tid)
    prov_check, err_resp = _provider_check(msg, provider)
    if not prov_check:
        return make_response(jsonify(err_resp), 500)


    ### API CORE ### 
    uuid = DopUtils.create_uuid()
    token = DopUtils.create_auth_token()
 
    start_session_ev = {
        "session" : str(uuid),
        "event": "start_session",
        "task": "", 
        "params": {
            "auth_token" : token,
            "session" : str(uuid), 
            "subject" : subject
        }
    }

    written, resp = _write_mess(provider, json.dumps(start_session_ev))
    if not written:
        return make_response(jsonify(resp)), 500
    else:
        resp = {
            'auth_token' : token,
            'session' : str(uuid)
            }
        return make_response(jsonify(resp)), 200




def _json_check(req) -> Tuple[bool, dict]: 
    ### MISSING application/json HEADER ###
    if not req.headers.get('Content-Type') == "application/json":
        logger.log(22701, LogSeverity.ERROR, 
            getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
            {"msg": "The request could not be validated, invalid content type header: expected application/json"})
        
        err_resp = {"err" : 1}
        return (False, err_resp) 
    
    return (True, {})

def _provider_check(msg, provider) -> Tuple[bool, dict]:
    
    log_severity = LogSeverity.CRITICAL if provider is None else LogSeverity.INFO
    logger.log(err, log_severity,
            getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
            {"msg": msg})

    ### CHECK PROVIDER ### 
    if provider is None:
        error = DopError(22703,f"An error occurred when writing request payload to output: provider is None.")
        logger.log(error.msg, LogSeverity.CRITICAL, 
                getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
                {"msg": error.msg})
        
        err_resp = {"err": 4}
        #msg = "The request could not be propagated to the DOP backend services due to missing provider."
        return (False, err_resp)
    
    return (True, {})


def _write_mess(provider, mess: str) -> Tuple[bool, dict]: 
    per = provider.write(mess)
    if per.isError():

        error = DopError(22702,"An error occurred when writing request payload to output.")
        error.perr = per
        logger.log(error.msg, LogSeverity.CRITICAL, 
            getframeinfo(currentframe()).filename, getframeinfo(currentframe()).lineno,
            {"msg": error.msg, "per": error.perr.to_dict()})
        
        err_resp = {"err": 3}
        # msg = "The request could not be propagated to the DOP backend services due to an internal error."
        return (False, err_resp) # 500
    else:
        
        success_resp = {"err": 0}
        #msg = "Your request is being processed by our system!\n"
        return (True, success_resp) # 200
    

if __name__=="__main__":
    app.run()
