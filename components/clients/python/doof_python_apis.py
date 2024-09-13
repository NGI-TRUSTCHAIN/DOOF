#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

import copy
import json
import signal
import sys
import time
import threading 


# import from packages and modules within the ecosteer project
from common.python.error import DopError
from common.python.utils import DopUtils 
from common.python.threads import DopStopEvent
from provider.python.presentation.output.provider_pres_output import outputPresentationProvider # abstract base class
from provider.python.presentation.input.provider_pres_input import inputPresentationProvider    # abstract base class

from components.clients.python.app_layer_protocol import AppProtocol
from components.clients.python.events import dop_events

global_stop_event = DopStopEvent()

def signalHandlerDefault(signalNumber, frame):
    print('Received:', signalNumber)

def signalHandlerExit(signalNumber, frame):
    #   set the exit event
    print('Exiting ...')
    global_stop_event.stop()

def signalManagement(): 
    signal.signal(signal.SIGTERM, signalHandlerExit)
    signal.signal(signal.SIGINT, signalHandlerExit)
    #signal.signal(signal.SIGQUIT, signalHandlerExit) # does not work on Windows

 

class DOOFPythonAPIs:
    """
    A module offering data ownership capabilities for python. The DOOF Python APIs are a collection
    of APIs which allow to set up a client which connects to the DOOF back-end to send 
    imperatives and receive notifications.  
    This class works as an access point to the client's functionalities and 
    as a data structure which stores information needed for a session with the back-end. 
    The DOOFPythonAPIs class has the responsibility of:
    - parsing the configuration file into a dictionary which is then passed to the more "infrastructural"
    layer of the Application Protocol instance
    - calling the Application Protocol APIs to load and configure the input and output providers 
    - defining the business layer logic, i.e. the workflow which allows a user to log in and send 
    the imperatives to the DOOF back-end, and which imperatives can be sent 
    - defining the callbacks that handle the back-end notifications  
    """
    
    def __init__(self, prov_available = False):
        # This class works as an access point 
        self._conf_file_path = None
        self._conf_dict = None
        self._stop_event = DopStopEvent()
        
        self._prov_available = prov_available 
        self._app_protocol = None

        # Application specific endpoints (also configured via conf file)
        self._endpoints = {
            'wbl_api' : '/dop/imperatives',
            'session_api' : '/dop/startsession',
            'admin_api': '/dop/syadmin',
            'login_api' : '/login-handler'
        }

        # SESSION INFO
        self._logged_in = False
        self._username = ""
        self._session = None 
        self._auth_token = None
        self._auth_header = {}
        
        # MLE INFO
        self._cipher_suite = None
        self._key = None 
        self._backend_ciphers = None 

        # synchronize with received events 
        self._custom_sync = {}
        self._login_sync = threading.Event() 
        self._login_sync.clear()
        self._start_session_sync = threading.Event()
        self._start_session_sync.clear()
        self._client_ready_sync = threading.Event() 
        self._client_ready_sync.clear()
        self._css_sync = threading.Event() 
        self._css_sync.clear()

        self._products_list_sync = threading.Event()
        self._products_list_sync.clear()
        self._pub_conf_sync = threading.Event()
        self._pub_conf_sync.clear()

        
        self._label_dop_account_info = dop_events.dop_account_info.get('event')
        self._label_dop_cipher_suite_selection = dop_events.dop_cipher_suite_selection.get('event')
        self._label_dop_client_ready = dop_events.dop_client_ready.get('event')
        self._label_dop_enable_identity = dop_events.dop_enable_identity.get('event')
        self._label_dop_product_create = dop_events.dop_product_create.get('event')
        self._label_dop_product_subscribe = dop_events.dop_product_subscribe.get('event')
        self._label_dop_product_subscriptions = dop_events.dop_product_subscriptions.get('event')
        self._label_dop_product_unsubscribe = dop_events.dop_product_unsubscribe.get('event')
        self._label_dop_products_list = dop_events.dop_products_list.get('event')
        self._label_dop_pub_configuration = dop_events.dop_pub_configuration.get('event')
        self._label_dop_purpose_create = dop_events.dop_purpose_create.get('event')
        self._label_dop_purpose_list = dop_events.dop_purpose_list.get('event')
        self._label_dop_sub_configuration = dop_events.dop_sub_configuration.get('event')
        self._label_dop_subscription_grant = dop_events.dop_subscription_grant.get('event')
        self._label_dop_subscription_info = dop_events.dop_subscription_info.get('event')
        self._label_dop_subscription_revoke = dop_events.dop_subscription_revoke.get('event')


        self._event_received_lock = threading.Lock()
        self._last_events_received = {
            self._label_dop_account_info : None, 
            self._label_dop_cipher_suite_selection : None,
            self._label_dop_client_ready: None,
            self._label_dop_enable_identity: None,
            self._label_dop_product_create: None,
            self._label_dop_product_subscribe: None,
            self._label_dop_product_subscriptions: None,
            self._label_dop_product_unsubscribe: None,
            self._label_dop_products_list: None, 
            self._label_dop_pub_configuration: None,
            self._label_dop_purpose_create : None,
            self._label_dop_purpose_list: None,
            self._label_dop_sub_configuration: None,
            self._label_dop_subscription_grant: None,
            self._label_dop_subscription_info: None, 
            self._label_dop_subscription_revoke : None,
        }

        self._configured = False


    @property 
    def endpoints(self):
        return self._endpoints

    @property 
    def custom_sync(self):
        return self._custom_sync 
    
    @property 
    def stop_event(self):
        return self._stop_event

    @property 
    def last_events_received(self):
        return self._last_events_received

    @property 
    def event_received_lock(self):
        return self._event_received_lock

    @property
    def username(self):
        return self._username 
    
    @username.setter
    def username(self, name):
        self._username = name
    
    
    @property
    def logged_in(self):
        return self._logged_in 
    
    @logged_in.setter
    def logged_in(self, logged_in):
        self._logged_in = logged_in


    @property
    def session(self):
        return self._session 
    
    @session.setter
    def session(self, session):

        self._session = session
        if self._app_protocol is not None: 
            self._app_protocol.curr_session = session

    @property 
    def auth_token(self):
        return self._auth_token
    
    @auth_token.setter
    def auth_token(self, auth):
        self._auth_token = auth

    @property 
    def auth_header(self):
        return self._auth_header

    @auth_header.setter 
    def auth_header(self, au):
        self._auth_header = au

    @property 
    def backend_ciphers(self):
        return self._backend_ciphers 
    
    @backend_ciphers.setter
    def backend_ciphers(self, ciphers):
        self._backend_ciphers = ciphers

    @property 
    def cipher_suite(self):
        return self._cipher_suite 

    @cipher_suite.setter 
    def cipher_suite(self, cipher):
        self._cipher_suite = cipher 
    
    @property 
    def key(self):
        return self._key
    
    @key.setter 
    def key(self, key):
        self._key = key
    
    @property 
    def login_sync(self):
        return self._login_sync
    
    @property 
    def start_session_sync(self):
        return self._start_session_sync
    
    @property 
    def client_ready_sync(self):
        return self._client_ready_sync

    @property
    def css_sync(self):
        return self._css_sync

    @property 
    def products_list_sync(self):
        return self._products_list_sync
    
    @property 
    def pub_conf_sync(self):
        return self._pub_conf_sync

    def init(self, conf_file) -> DopError:
        self._conf_file_path = conf_file
        err, conf_dict = DopUtils.parse_yaml_configuration(self._conf_file_path)
        if err.isError():
            return err 
        self._conf_dict = conf_dict 
        if 'endpoints' in conf_dict:
            self._endpoints = conf_dict.get('endpoints')
        self._app_protocol = AppProtocol(conf_file, self._stop_event, prov_available=self._prov_available)
        self._app_protocol.set_userdata(self)
        
        self._app_protocol.startsession_endpoint = self._endpoints['session_api']
        self._app_protocol.login_endpoint = self._endpoints['login_api']
    
        err = self._app_protocol.load_providers(self._conf_dict)
        if err.isError():
            return err
        # Handlers for events: they are defined in the doof_python_apis module
        # and used by the application protocol on dipatching of events
        self._app_protocol.set_on_dop_account_info(
            self.dop_account_info_handler
            )
        self._app_protocol.set_on_dop_cipher_suite_selection(
            self.dop_cipher_suite_selection_handler
            )
        self._app_protocol.set_on_dop_client_ready(
            self.dop_client_ready_handler
            )
        self._app_protocol.set_on_dop_enable_identity(
            self.dop_enable_identity_handler
            )
        self._app_protocol.set_on_dop_product_create(
            self.dop_product_create_handler
            )
        self._app_protocol.set_on_dop_product_subscribe(
            self.dop_product_subscribe_handler
            )
        self._app_protocol.set_on_dop_product_subscriptions(
            self.dop_product_subscriptions_handler
            )
        self._app_protocol.set_on_dop_product_unsubscribe(
            self.dop_product_unsubscribe_handler
            )
        self._app_protocol.set_on_dop_products_list(
            self.dop_products_list_handler
            )
        self._app_protocol.set_on_dop_pub_configuration(
            self.dop_pub_configuration_handler
            )
        self._app_protocol.set_on_dop_purpose_create(
            self.dop_purpose_create_handler
            )
        self._app_protocol.set_on_dop_purpose_list(
            self.dop_purpose_list_handler
            )
        self._app_protocol.set_on_dop_sub_configuration(
            self.dop_sub_configuration_handler
            )
        self._app_protocol.set_on_dop_subscription_grant(
            self.dop_subscription_grant_handler
            )
        self._app_protocol.set_on_dop_subscription_info(
            self.dop_subscription_info_handler
            )
        self._app_protocol.set_on_dop_subscription_revoke(
            self.dop_subscription_revoke_handler
            )

        self._app_protocol.set_on_other_callback(self.other_handler)
        self._app_protocol.set_on_login_response(self.login_response_handler)
        self._app_protocol.set_on_start_session_response(self.start_session_handler)
        self._app_protocol.set_on_http_response(self.http_response_handler)
        
       
        self._configured = True
        return DopError()

    def open_output(self) -> DopError:
        if not self._configured: 
            return DopError(1, """You must first of all initialize the APIs by passing the\n
                             configuration file: apis.init(conf_file)""")
            

        err = self._app_protocol.init_output_provider(self._conf_dict, "")
        if err.isError():
            return err 
        return self._app_protocol.open_output_provider()
        

    def open_input(self, session) -> DopError:
        
        if not self._configured: 
            return DopError(1, """You must first of all initialize the APIs by passing the\n
                             configuration file: apis.init(conf_file)""")
            
        # init input provider needs the session which is the subtopic to which 
        # to subscribe; it is given by the dop gateway, so this code should be 
        # moved to a specific method 
        err = self._app_protocol.init_input_provider(self._conf_dict, session)
        if err.isError(): 
            return err 
        return self._app_protocol.open_input_provider()


    def close(self):

        err = self._app_protocol.close_input_provider()
        err = self._app_protocol.close_output_provider()
        return err

 
    def tracefun(self, called):
        print(f"doof_python_apis - {called}")
    
    def tracemsg(self, msg: str):
        print(f"{msg}")

    def login(self, username, password):
        payload = {"username": username, "password": password}
        request = f"@JSON;{json.dumps(payload)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['login_api']) 
        print(err)
        return err
    
    def start_session(self, username = None):
        if not self.logged_in:
            print("You must first of all log in.")
            return DopError(1, "Not logged in")
        if username is None: 
            username = self._username
        payload = {"sub": username}
        request = f"@JSON;{json.dumps(payload)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['session_api'], self.auth_header) 
        print(err)
        return err 

    def start_session_handler(self, endpoint, message: str, userdata):
        # Client has sent to DOOF Gateway a startsession and it has received the 
        # HTTP reply with auth token and session, which it uses for subscribing to 
        # mqtt broker topic; after subscription, client sends dop_client_ready event 
        ud: DOOFPythonAPIs = userdata
        ud.tracefun("start_session_handler")
        mess_dict = json.loads(message)
        #print(mess_dict)
        response_content = mess_dict.get('response_content')
        session_dict = json.loads(response_content)
        session_uuid = session_dict.get('session')
        ud.session = session_uuid
        auth_token = session_dict.get('auth_token')
        ud.auth_token = auth_token
        print(f"session uuid: {session_uuid}; auth token: {auth_token}")
        ud.start_session_sync.set()
        # have a different function sending a dop_client_ready when the start_session was set

    def send_custom_event(self, event, options=None):
        request = f"@JSON;{json.dumps(event)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        return err

    def dop_account_info(self, task = ''):
        # session and auth_token are handled in the background, as they are more infrastructural 
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
        
        ev = copy.deepcopy(dop_events.dop_account_info)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token
        # send event
        request = f"@JSON;{json.dumps(ev)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        print(err)
        return err


    def dop_cipher_suite_selection(self, cipher_suite: dict, cipher_key, task = ''):
        # Caller of this method should check: 
        # - input provider was opened
        # - client_ready was sent and notification was received 
        # Only call this method after having chosen a cipher_suite 
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
        
        ev = copy.deepcopy(dop_events.dop_cipher_suite_selection)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        # info specific for event
        ev['params']['cipher_suite'] = cipher_suite 
        ev['params']['cipher_key'] = cipher_key

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        print(err) 
        return err 
    
    def dop_client_ready(self, task = ""):
        
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
        ev = copy.deepcopy(dop_events.dop_client_ready)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        print(err)
        return err

    def dop_enable_identity(self, subject:str, screen: str, recipient="", task=""):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
        ev = copy.deepcopy(dop_events.dop_enable_identity)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        # info specific for event
        ev['params']['subject'] = subject
        ev['params']['screen_name'] = screen
        ev['params']['recipient'] = recipient

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request,  self.endpoints['admin_api'], self.auth_header)
        return err

    def dop_recipient_set(self, subject: str, recipient: str, task=""):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
        ev = copy.deepcopy(dop_events.dop_recipient_set)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        # info specific for event
        ev['params']['subject'] = subject
        ev['params']['recipient'] = recipient

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['admin_api'], self.auth_header)
        return err 

    def dop_product_create(self, label, price, period, data_origin = "", task=""):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
        ev = copy.deepcopy(dop_events.dop_product_create)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        # info specific for event
        ev['params']['label'] = label
        ev['params']['price'] = price
        ev['params']['period'] = period
        ev['params']['data_origin_id'] = data_origin
        

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        return err
        

    def dop_product_subscribe(self, product_id: str, purpose_id: str, pre_auth_code = None, task=""):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
        ev = copy.deepcopy(dop_events.dop_product_subscribe)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        # info specific for event
        ev['params']['product_id'] = product_id
        ev['params']['purpose_id'] = purpose_id 

        if pre_auth_code is not None: 
            ev['params']['pre_auth_code'] = pre_auth_code 

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        return err
        

    def dop_product_subscriptions(self, product_id: str, query_type: str, task=""):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
        ev = copy.deepcopy(dop_events.dop_product_subscriptions)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        # info specific for event
        ev['params']['product_id'] = product_id 
        ev['params']['type'] = query_type

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        return err
        
    def dop_product_unsubscribe(self, subscription_id: str, task=""):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
        ev = copy.deepcopy(dop_events.dop_product_unsubscribe)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        # info specific for event
        ev['params']['subscription_id'] = subscription_id

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        return err
        

    def dop_products_list(self, query_type: str='all', filter:dict = {}, task=""):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
        ev = copy.deepcopy(dop_events.dop_products_list)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        # info specific for event
        ev['params']['type'] = query_type
        ev['params']['filter'] = filter 

        #if task is not None and task != "": 
            #self._tasks.add(task)

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        return err
        

    def dop_pub_configuration(self, product_id:str, task=""):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
        ev = copy.deepcopy(dop_events.dop_pub_configuration)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        # info specific for event
        ev['params']['product_id'] = product_id

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        return err

    def dop_purpose_create(self, label: str, content:str, task=""):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in") 
        
        ev = copy.deepcopy(dop_events.dop_purpose_create)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        # info specific for event
        ev['params']['label'] = label
        ev['params']['content'] = content 

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        return err 
    

    def dop_purpose_list(self, task=""):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
        ev = copy.deepcopy(dop_events.dop_purpose_list)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        return err 
        
    def dop_sub_configuration(self, subscription_id:str, task=""):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
        
        ev = copy.deepcopy(dop_events.dop_sub_configuration)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        # info specific for event
        ev['params']['subscription_id'] = subscription_id

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        return err
        
        

    def dop_subscription_grant(self, subscription_id:str, task=""):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
        
        ev = copy.deepcopy(dop_events.dop_subscription_grant)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        # info specific for event
        ev['params']['subscription_id'] = subscription_id

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        return err
        

    def dop_subscription_info(self, subscription_id:str, task=""):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in") 
        ev = copy.deepcopy(dop_events.dop_subscription_info)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        # info specific for event
        ev['params']['subscription_id'] = subscription_id

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        return err 
        

    def dop_subscription_revoke(self, subscription_id:str, task=""):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
        ev = copy.deepcopy(dop_events.dop_subscription_revoke)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        # info specific for event
        ev['params']['subscription_id'] = subscription_id

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        print(request)
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        return err
        
    

    # HANDLERS 
    def dop_account_info_handler(self, message_topic, message_payload, userdata):
        ud: DOOFPythonAPIs = userdata 
        ud.tracefun("dop_account_info_handler")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        with ud.event_received_lock:
            ud.last_events_received[ud._label_dop_account_info] = message_payload

    def dop_cipher_suite_selection_handler(self, message_topic, message_payload, userdata):
        ud: DOOFPythonAPIs = userdata 
        ud.tracefun("dop_cipher_suite_selection_handler")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        with ud.event_received_lock:
            ud.last_events_received[ud._label_dop_cipher_suite_selection] = message_payload
        
        ud.css_sync.set()

    def dop_client_ready_handler(self, message_topic, message_payload, userdata):
        ud: DOOFPythonAPIs = userdata 
        ud.tracefun("dop_client_ready_handler")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        json_payload = json.loads(message_payload)

        if 'params' in json_payload and 'cipher_suites' in json_payload['params']:
            cipher_suites = json_payload['params']['cipher_suites']
            ud.backend_ciphers = cipher_suites
            
        with ud.event_received_lock:
            ud.last_events_received[ud._label_dop_client_ready] = message_payload
        
        ud.client_ready_sync.set()

    def dop_enable_identity_handler(self, message_topic, message_payload, userdata):
        ud: DOOFPythonAPIs = userdata 
        ud.tracefun("dop_enable_identity_handler")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        with ud.event_received_lock:
            ud.last_events_received[ud._label_dop_enable_identity] = message_payload
        
    
    def dop_product_create_handler(self, message_topic, message_payload, userdata):
        ud: DOOFPythonAPIs = userdata 
        ud.tracefun("dop_product_create_handler")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        with ud.event_received_lock:
            ud.last_events_received[ud._label_dop_product_create] = message_payload
        
    
    def dop_product_subscribe_handler(self, message_topic, message_payload, userdata):
        ud: DOOFPythonAPIs = userdata 
        ud.tracefun("dop_product_subscribe_handler")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        with ud.event_received_lock:
            ud.last_events_received[ud._label_dop_product_subscribe] = message_payload

        if self._label_dop_product_subscribe in ud.custom_sync:
            sync_event: threading.Event = ud.custom_sync['dop_product_subscribe']
            sync_event.set()    
    
    def dop_product_subscriptions_handler(self, message_topic, message_payload, userdata):
        ud: DOOFPythonAPIs = userdata 
        ud.tracefun("dop_product_subscriptions_handler")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        with ud.event_received_lock:
            ud.last_events_received[ud._label_dop_product_subscriptions] = message_payload
        
    
    def dop_product_unsubscribe_handler(self, message_topic, message_payload, userdata):
        ud: DOOFPythonAPIs = userdata 
        ud.tracefun("dop_product_unsubscribe_handler")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        with ud.event_received_lock:
            ud.last_events_received[ud._label_dop_product_unsubscribe] = message_payload
        
    
    def dop_products_list_handler(self, message_topic, message_payload, userdata):
        ud: DOOFPythonAPIs = userdata 
        ud.tracefun("dop_products_list_handler")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        with ud.event_received_lock:
            ud.last_events_received[ud._label_dop_products_list] = message_payload
        ud.products_list_sync.set()
    
    def dop_pub_configuration_handler(self, message_topic, message_payload, userdata):
        """
        This handler - or the application logic using it - should receive pub
        configuration, decode the base64 text, and write the content to a file.
        """
        ud: DOOFPythonAPIs = userdata 
        ud.tracefun("dop_pub_configuration_handler")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        with ud.event_received_lock:
            ud.last_events_received[ud._label_dop_pub_configuration] = message_payload
        ud.pub_conf_sync.set()
    
    def dop_purpose_create_handler(self, message_topic, message_payload, userdata):
        ud: DOOFPythonAPIs = userdata 
        ud.tracefun("dop_purpose_create_handler")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        with ud.event_received_lock:
            ud.last_events_received[ud._label_dop_purpose_create] = message_payload
        
    
    def dop_purpose_list_handler(self, message_topic, message_payload, userdata):
        ud: DOOFPythonAPIs = userdata 
        ud.tracefun("dop_purpose_list")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        with ud.event_received_lock:
            ud.last_events_received[ud._label_dop_purpose_list] = message_payload
        
    
    def dop_sub_configuration_handler(self, message_topic, message_payload, userdata):
        ud: DOOFPythonAPIs = userdata 
        ud.tracefun("dop_sub_configuration_handler")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        with ud.event_received_lock:
            ud.last_events_received[ud._label_dop_sub_configuration] = message_payload
        
        if self._label_dop_sub_configuration in ud.custom_sync:
            sync_event: threading.Event = ud.custom_sync[self._label_dop_sub_configuration]
            sync_event.set()    
    
        
    def dop_subscription_grant_handler(self, message_topic, message_payload, userdata):
        ud: DOOFPythonAPIs = userdata 
        ud.tracefun("dop_subscription_grant_handler")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        with ud.event_received_lock:
            ud.last_events_received[ud._label_dop_subscription_grant] = message_payload
        
    
    def dop_subscription_info_handler(self, message_topic, message_payload, userdata):
        ud: DOOFPythonAPIs = userdata 
        ud.tracefun("dop_subscription_info_handler")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        with ud.event_received_lock:
            ud.last_events_received[ud._label_dop_subscription_info] = message_payload
        
        if self._label_dop_subscription_info in ud.custom_sync: 
            sync_event: threading.Event = ud.custom_sync[self._label_dop_subscription_info]
            sync_event.set()

    def dop_subscription_revoke_handler(self, message_topic, message_payload, userdata):
        ud: DOOFPythonAPIs = userdata 
        ud.tracefun("dop_subscription_revoke_handler")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        with ud.event_received_lock:
            ud.last_events_received[ud._label_dop_subscription_revoke] = message_payload
        
    
    
        

    def other_handler(self, message_topic, message_payload, userdata):
        ud: DOOFPythonAPIs = userdata 
        ud.tracefun("other_handler")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        

    def login_response_handler(self, endpoint, message: str, userdata):
        ud: DOOFPythonAPIs = userdata
        ud.tracefun("login_response_handler")
        ud.tracemsg(endpoint)
        ud.tracemsg(f"@REPLY;{message}")
        mess_dict = json.loads(message)
        #print(mess_dict)
        response_content = mess_dict.get('response_content')
        response_headers = mess_dict.get('response_headers')
        if isinstance(response_content, str) and response_content.lower() == "login successful":
            # login was performed correctly, find the authorization headers 
            auth_header = {}
            for header in response_headers: 
                #print(header)
                if header[0].lower() == 'authorization':
                    auth_header = {header[0]: header[1]}
                    ud.auth_header = auth_header
                    ud.logged_in = True
                    ud.login_sync.set()

            if not ud.logged_in:
                print("No authorization header found. Login failed.")
            # have a different function which runs a loop and waits for 
            # login_sync to be set in order to send a start_session
    

    

    def http_response_handler(self, endpoint, message: str, userdata):
        ud: DOOFPythonAPIs = userdata
        ud.tracefun("http_response_handler")
        ud.tracemsg(endpoint)
        ud.tracemsg(f"@REPLY;{message}")
        mess_dict = json.loads(message)
        #print(mess_dict)
        response_content = mess_dict.get('response_content')
        
    def setup_unauth_session(self, username):
        """
        Call this method to setup a non-authenticated session (don't use authentication
        server)
        """
        self.open_output()
        self.username = username
        
        self.logged_in = True
        self.start_session(username)

        while not self.start_session_sync.is_set():
            self.start_session_sync.wait(0.5)
        self.start_session_sync.clear()

        err = self.open_input(self.session)
        if err.isError():
            print("Could not create a session with the back-end")
        
        self.dop_client_ready(1)

        while not self.client_ready_sync.is_set():
            self.client_ready_sync.wait(0.5)
        self.client_ready_sync.clear()
    
        chosen_cipher_suite = self._app_protocol.mle_client.choose_ciphersuite(self.backend_ciphers)
        keylength_bytes = int(int(chosen_cipher_suite['keylength'])/8)
        self._app_protocol.mle_client.generate_key(keylength_bytes)
        key_b64 = self._app_protocol.mle_client.b64_key

        self.dop_cipher_suite_selection(chosen_cipher_suite, key_b64)

        while not self.css_sync.is_set():
            self.css_sync.wait(0.5)
        self.css_sync.clear()
        

    
    def setup_new_session(self, username, password):
        """ Call this method to setup a new authenticated session for the supplied user.
            The DOOFPythonAPIs should have already been initialized with the configuration 
            file which indicates the servers to connect to. 
        """
        self.open_output()
        self.username = username
        
        self.login(username, password)

        while not self.login_sync.is_set():
            self.login_sync.wait(0.5)
        self.login_sync.clear()

        self.start_session(username)

        while not self.start_session_sync.is_set():
            self.start_session_sync.wait(0.5)
        self.start_session_sync.clear()

        err = self.open_input(self.session)
        if err.isError():
            print("Could not create a session with the back-end")
        
        self.dop_client_ready(1)

        while not self.client_ready_sync.is_set():
            
            self.client_ready_sync.wait(0.5)
            #self.dop_client_ready(1)

        self.client_ready_sync.clear()
    
        chosen_cipher_suite = self._app_protocol.mle_client.choose_ciphersuite(self.backend_ciphers)
        keylength_bytes = int(int(chosen_cipher_suite['keylength'])/8)
        self._app_protocol.mle_client.generate_key(keylength_bytes)
        key_b64 = self._app_protocol.mle_client.b64_key

        self.dop_cipher_suite_selection(chosen_cipher_suite, key_b64)

        while not self.css_sync.is_set():
            self.css_sync.wait(0.5)
        self.css_sync.clear()

        
import base64
if __name__ == '__main__':
    signalManagement()
    
    apis = DOOFPythonAPIs()
    apis.init(sys.argv[1])

    #apis.open_output() 
    
    username = input("username:")
    password = input("password:")
    apis.username = username


    apis.setup_new_session(username, password)


    while not global_stop_event.is_exiting():
        
        global_stop_event.wait(1)

    apis.stop_event.stop()
    apis.stop_event.wait(2)
    
    apis.close()

    print("closed")