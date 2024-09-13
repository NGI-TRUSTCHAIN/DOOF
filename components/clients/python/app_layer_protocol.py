#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

import json
import os
import re
import sys
import threading 
from typing import Callable

# import from packages and modules within the ecosteer project
from common.python.error import DopError 
from common.python.utils import DopUtils 
from common.python.threads import DopStopEvent
from provider.python.presentation.output.provider_pres_output import outputPresentationProvider # an abstract class
from provider.python.presentation.input.provider_pres_input import inputPresentationProvider 


from components.clients.python.mle_client import MLE_Client
from components.clients.python.events import dop_events

class AppProtocol:
    """
    This class is an intermediary between the modules that take the user input 
    and the providers that are responsible of interacting with the back-end.
    It initializes both input and output providers based on the indications
    found in the configuration file passed as parameters.
    """

    def __init__(self, confFilePath:str, stopEvent: DopStopEvent, prov_available = False):
        self._confFilePath = confFilePath
        self._inputProvider: inputPresentationProvider = None
        self._outputProvider: outputPresentationProvider = None   
        self._stopEvent = stopEvent
        self._prov_available = prov_available

        self._curr_session = None
        # TODO: the following endpoints should be configurable
        self._login_endpoint = "/login-handler"
        self._startsession_endpoint = "/dop/startsession"
        #self._imperatives_endpoint = "/dop/imperatives"     # this is taken from conf file
        #self._admin_endpoint = "/dop/sysadmin"


        self._input_configured = False
        self._output_configured = False
    
        self._mle_client = MLE_Client(self._prov_available)
        #self._mle_client.init(confFilePath)

        self._callbackLock = threading.Lock()

        self._upperUserdata = None

        # USER-DEFINED CALLBACK FUNCTIONS 
        self._on_dop_account_info: Callable = None
        self._on_dop_cipher_suite_selection: Callable = None 
        self._on_dop_client_ready: Callable = None
        self._on_dop_enable_identity: Callable = None 
        self._on_dop_product_create: Callable = None 
        self._on_dop_product_subscribe: Callable = None 
        self._on_dop_product_subscriptions: Callable = None 
        self._on_dop_product_unsubscribe: Callable = None 
        self._on_dop_products_list: Callable = None
        self._on_dop_pub_configuration: Callable = None 
        self._on_dop_purpose_create: Callable = None 
        self._on_dop_purpose_list: Callable = None 
        self._on_dop_sub_configuration: Callable = None 
        self._on_dop_subscription_grant: Callable = None
        self._on_dop_subscription_info: Callable = None 
        self._on_dop_subscription_revoke: Callable = None 

        self._on_other_function: Callable = None
        self._on_login_response: Callable = None
        self._on_start_session_response: Callable = None
        self._on_http_response: Callable = None

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
        


    @property 
    def curr_session(self):
        return self._curr_session 

    @curr_session.setter
    def curr_session(self, session):
        self._curr_session = session

    @property 
    def mle_client(self):
        return self._mle_client 
    
    @property 
    def login_endpoint(self):
        return self._login_endpoint

    
    @login_endpoint.setter 
    def login_endpoint(self, login):
        self._login_endpoint = login

    #@property
    #def admin_endpoint(self):
    #    return self._admin_endpoint
    
    @property 
    def startsession_endpoint(self):
        return self._startsession_endpoint

    @startsession_endpoint.setter
    def startsession_endpoint(self, startsession):
        self._startsession_endpoint = startsession

    @property
    def callbackLock(self):
        return self._callbackLock

   
    def set_userdata(self, userdata):
        """
        To be used by the upper layer to set the userdata
        for the callback functions.
        """
        self._upperUserdata = userdata

    
    # OWN CALLBACKS TO BE ASSIGNED TO PROVIDERS #

    def error_callback(self, err: DopError, userdata):
        # TODO maybe add an upper layer callback for this as well 
        #print("This is the callback for the error.")
        #print(str(err.code) + ' ' + err.msg)
        return

    def data_callback(self, message_topic: str, message_payload: str, userdata):

       
        """
        Callback to be assigned to the provider for the handling of received data.
        See provider.py: 
            For assignment -> set_on_data_callback 
            For usage -> _on_data, _on_data_fun
        Manages the received message in a critical section.
        
        The parameter 'userdata' is a user-defined structure that needs to be passed
        to this method in order to set the correct context for the handling of the data.
        In this case, it is an instance of the AppProtocol itself. The userdata is set 
        when initializing the provider, with set_userdata, and is passed as 
        a parameter to this method by the provider, in the _on_data function.
        """
        # enter CS 
        with self._callbackLock:
           
            #if it found an enwrapped event, unwrap it with the help of an encryption module (TODO)
            if message_topic != None and message_payload != None: 
                to_handle = message_payload
                if bool(re.match(".*(cipher_suite_name\":)\s*.*", message_payload)): # mle == 1
                    
                    print("\nMLE FRAME")
                    print(message_payload)
                    message_dict = json.loads(message_payload)
                    
                    if  self._curr_session.upper() in message_topic.upper() :
                        # NOTE only try to dedopify messages that arrive 
                        # on current active session, for which the key is present 
                        print("DMP PAYLOAD")
                        err, to_handle = self._mle_client.handle_mle_event(message_dict) # MLEClient.unwrap() ; mle(dmp) event 
                        print(to_handle)
                        
                        print("BACK TO BLL\n")

                # message_topic is the events/session topic on the broker
                self._data_callback(message_topic, to_handle, userdata)
        # exit CS 

    def _data_callback(self, message_topic: str, message_payload: str, userdata):
        """
        Internal handling and dispatching of the plaintext Event received from the back-end
        """
        app_protocol: AppProtocol = userdata 
    
        if message_topic != None and message_payload != None: 
            

            if bool(re.match(".*(event\":)\s*(\"dop_account_info\").*", message_payload)):
                app_protocol.on_dop_account_info(message_topic, message_payload)

            elif bool(re.match(f".*(event\":)\s*(\"{self._label_dop_cipher_suite_selection}\").*", message_payload)): 
                app_protocol.on_dop_cipher_suite_selection(message_topic, message_payload)
            
            elif bool(re.match(f".*(event\":)\s*(\"{self._label_dop_client_ready}\").*", message_payload)):
                app_protocol.on_dop_client_ready (message_topic, message_payload)

            elif bool(re.match(f".*(event\":)\s*(\"{self._label_dop_enable_identity}\").*", message_payload)):
                app_protocol.on_dop_enable_identity (message_topic, message_payload)

            elif bool(re.match(f".*(event\":)\s*(\"{self._label_dop_product_create}\").*", message_payload)):
                app_protocol.on_dop_product_create(message_topic, message_payload)

            elif bool(re.match(f".*(event\":)\s*(\"{self._label_dop_product_subscribe}\").*", message_payload)):
                app_protocol.on_dop_product_subscribe (message_topic, message_payload)

            elif bool(re.match(f".*(event\":)\s*(\"{self._label_dop_product_subscriptions}\").*", message_payload)):
                app_protocol.on_dop_product_subscriptions (message_topic, message_payload)

            elif bool(re.match(f".*(event\":)\s*(\"{self._label_dop_product_unsubscribe}\").*", message_payload)):
                app_protocol.on_dop_product_unsubscribe (message_topic, message_payload)

            elif bool(re.match(f".*(event\":)\s*(\"{self._label_dop_products_list}\").*", message_payload)):
                app_protocol.on_dop_products_list (message_topic, message_payload)

            elif bool(re.match(f".*(event\":)\s*(\"{self._label_dop_pub_configuration}\").*", message_payload)):
                app_protocol.on_dop_pub_configuration (message_topic, message_payload)

            elif bool(re.match(f".*(event\":)\s*(\"{self._label_dop_purpose_create}\").*", message_payload)):
                app_protocol.on_dop_purpose_create (message_topic, message_payload)

            elif bool(re.match(f".*(event\":)\s*(\"{self._label_dop_purpose_list}\").*", message_payload)):
                app_protocol.on_dop_purpose_list (message_topic, message_payload)

            elif bool(re.match(f".*(event\":)\s*(\"{self._label_dop_sub_configuration}\").*", message_payload)):
                app_protocol.on_dop_sub_configuration (message_topic, message_payload)

            elif bool(re.match(f".*(event\":)\s*(\"{self._label_dop_subscription_grant}\").*", message_payload)):
                app_protocol.on_dop_subscription_grant (message_topic, message_payload)

            elif bool(re.match(f".*(event\":)\s*(\"{self._label_dop_subscription_info}\").*", message_payload)):
                app_protocol.on_dop_subscription_info (message_topic, message_payload)

            elif bool(re.match(f".*(event\":)\s*(\"{self._label_dop_subscription_revoke}\").*", message_payload)):
                app_protocol.on_dop_subscription_revoke(message_topic, message_payload)

            elif bool(re.match(f".*({self.login_endpoint}).*", message_topic)):
                app_protocol.on_login_response(message_topic, message_payload)

            elif bool(re.match(f".*({self._startsession_endpoint}).*", message_topic)):
                app_protocol.on_start_session_response(message_topic, message_payload)

            elif bool(re.match(".*(HTTP REPLY).*", message_topic)): 
                app_protocol.on_http_response(message_topic, message_payload)

            # ELSE ALL THE OTHER POSSIBLE NOTIFICATIONS
            else:
                app_protocol.on_other(mess_topic= message_topic, mess_payload= message_payload)
            print("\n") 
        return

    def on_encrypted_event(self, message_topic: str, message_payload):
        print(f"21600; {message_payload}")


    # ASSIGN THE USER-DEFINED CALLBACKS #
    def set_on_dop_account_info(self, callback: Callable):
        self._on_dop_account_info = callback

    def set_on_dop_cipher_suite_selection(self, callback: Callable):
        self._on_dop_cipher_suite_selection = callback

    def set_on_dop_client_ready(self, callback: Callable):
        self._on_dop_client_ready = callback

    def set_on_dop_enable_identity(self, callback: Callable):
        self._on_dop_enable_identity = callback

    def set_on_dop_product_create(self, callback: Callable):
        self._on_dop_product_create = callback

    def set_on_dop_product_subscribe(self, callback: Callable):
        self._on_dop_product_subscribe = callback

    def set_on_dop_product_subscriptions(self, callback: Callable):
        self._on_dop_product_subscriptions = callback

    def set_on_dop_product_unsubscribe(self, callback: Callable):
        self._on_dop_product_unsubscribe = callback

    def set_on_dop_products_list(self, callback: Callable):
        self._on_dop_products_list = callback

    def set_on_dop_pub_configuration(self, callback: Callable):
        self._on_dop_pub_configuration = callback

    def set_on_dop_purpose_create(self, callback: Callable):
        self._on_dop_purpose_create = callback

    def set_on_dop_purpose_list(self, callback: Callable):
        self._on_dop_purpose_list = callback

    def set_on_dop_sub_configuration(self, callback: Callable):
        self._on_dop_sub_configuration = callback
    
    def set_on_dop_subscription_grant(self, callback: Callable):
        self._on_dop_subscription_grant = callback

    def set_on_dop_subscription_info(self, callback: Callable):
        self._on_dop_subscription_info = callback

    def set_on_dop_subscription_revoke(self, callback: Callable):
        self._on_dop_subscription_revoke = callback
    
    
    # unknown notification event 
    def set_on_other_callback(self, other_callback: Callable):
        self._on_other_function = other_callback 

    
    def set_on_login_response(self, login_response_callback: Callable):
        self._on_login_response = login_response_callback 
    
    def set_on_start_session_response(self, callback: Callable):
        self._on_start_session_response = callback 

    def set_on_http_response(self, http_response_callback: Callable):
        self._on_http_response = http_response_callback 


    # CALL THE USER DEFINED CALLBACKS, IF THESE WERE SET #
    
    def on_dop_account_info(self, mess_topic, mess_payload):
        """
        Function to be called upon receival of an 'dop_account_info'
        event.
        """
        if self._on_dop_account_info != None:
            self._on_dop_account_info(mess_topic, mess_payload, self._upperUserdata)

    def on_dop_cipher_suite_selection(self, mess_topic, mess_payload):
        if self._on_dop_cipher_suite_selection != None:
            self._on_dop_cipher_suite_selection(mess_topic, mess_payload, self._upperUserdata)
          
    def on_dop_client_ready(self, mess_topic, mess_payload):
        if self._on_dop_client_ready != None:
            self._on_dop_client_ready(mess_topic, mess_payload, self._upperUserdata)

    def on_dop_enable_identity(self, mess_topic, mess_payload):
        if self._on_dop_enable_identity != None:
            self._on_dop_enable_identity(mess_topic, mess_payload, self._upperUserdata)
    
    def on_dop_product_create(self, mess_topic, mess_payload):
        if self._on_dop_product_create != None:
            self._on_dop_product_create(mess_topic, mess_payload, self._upperUserdata)
    
    def on_dop_product_subscribe(self, mess_topic, mess_payload):
        if self._on_dop_product_subscribe != None:
            self._on_dop_product_subscribe(mess_topic, mess_payload, self._upperUserdata)

    
    def on_dop_product_subscriptions(self, mess_topic, mess_payload):
        if self._on_dop_product_subscriptions != None:
            self._on_dop_product_subscriptions(mess_topic, mess_payload, self._upperUserdata)
    
    def on_dop_product_unsubscribe(self, mess_topic, mess_payload):
        if self._on_dop_product_unsubscribe != None:
            self._on_dop_product_unsubscribe(mess_topic, mess_payload, self._upperUserdata)

    def on_dop_products_list(self, mess_topic, mess_payload):
        if self._on_dop_products_list != None:
            self._on_dop_products_list(mess_topic, mess_payload, self._upperUserdata)

    def on_dop_pub_configuration(self, mess_topic, mess_payload):
        if self._on_dop_pub_configuration != None:
            self._on_dop_pub_configuration(mess_topic, mess_payload, self._upperUserdata)      
    
    def on_dop_purpose_create(self, mess_topic, mess_payload):
        if self._on_dop_purpose_create != None:
            self._on_dop_purpose_create(mess_topic, mess_payload, self._upperUserdata)

    def on_dop_purpose_list(self, mess_topic, mess_payload):
        if self._on_dop_purpose_list != None:
            self._on_dop_purpose_list(mess_topic, mess_payload, self._upperUserdata)

    def on_dop_sub_configuration(self, mess_topic, mess_payload):
        if self._on_dop_sub_configuration != None:
            self._on_dop_sub_configuration(mess_topic, mess_payload, self._upperUserdata)

    def on_dop_subscription_grant(self, mess_topic, mess_payload):
        if self._on_dop_subscription_grant != None:
            self._on_dop_subscription_grant(mess_topic, mess_payload, self._upperUserdata)

    def on_dop_subscription_info(self, mess_topic, mess_payload):
        if self._on_dop_subscription_info != None:
            self._on_dop_subscription_info(mess_topic, mess_payload, self._upperUserdata)

    def on_dop_subscription_revoke(self, mess_topic, mess_payload):
        if self._on_dop_subscription_revoke != None:
            self._on_dop_subscription_revoke(mess_topic, mess_payload, self._upperUserdata)
        

    def on_other(self, mess_topic, mess_payload):
        """This functions handles any other unknown back-end event."""
        if self._on_other_function != None:
            self._on_other_function(mess_topic, mess_payload, self._upperUserdata)

    def on_start_session_response(self, endpoint, mess_payload):
        if self._on_start_session_response != None:
            self._on_start_session_response(endpoint, mess_payload, self._upperUserdata)


    def on_login_response(self, endpoint, mess_payload):
        if self._on_login_response != None:
            self._on_login_response(endpoint, mess_payload, self._upperUserdata)

    def on_http_response(self, endpoint, mess_payload):
        if self._on_http_response != None: 
            self._on_http_response(endpoint, mess_payload, self._upperUserdata)
 
    
    def load_input_provider(self, configuration_dict) -> DopError:

        if ('inputProvider' in configuration_dict) == False:
            return  (DopError(21110, 'Configuration value error; inputProvider key is undefined/missing.'))
        
        input_configuration: dict = configuration_dict['inputProvider']
        tupleLoadProvider = DopUtils.load_provider(input_configuration, self._prov_available)
        if tupleLoadProvider[0].isError():
            return tupleLoadProvider[0]
        self._input_provider = tupleLoadProvider[1]

        print("21262; Input provider successfully loaded.")
        return DopError()

    def init_input_provider(self, configuration_dict, session: str) -> DopError:
        # data callbacks
        if self._input_provider is None:
            return DopError(1)
        
        self._input_provider.set_userdata(self)
        self._input_provider.set_on_data_callback(self.data_callback) 
        self._input_provider.set_on_error_callback(self.error_callback)
        self._input_provider.attach_stop_event(self._stopEvent)
        
        input_configuration: dict = configuration_dict['inputProvider']
        input_confstring: str = input_configuration['configuration']
        # Needed for the dynamic change in session of every client
        input_confstring = input_confstring.replace('%SESSION%', session)

        err: DopError = self._input_provider.init(input_confstring)
        if err.isError():
            return err 

        self._input_configured = True
        return DopError()
        


    def load_configure_input_provider(self, configuration_dict, session: str) -> DopError:
        
        err = self.load_input_provider(configuration_dict)
        if err.isError(): 
            return err 
        return self.init_input_provider(configuration_dict, session)

    def load_output_provider(self, configuration_dict) -> DopError:
        if ('outputProvider' in configuration_dict) == False:
            return (DopError(21111, 'Configuration value error; outputProvider key is undefined/missing.'))
        
        output_configuration: dict = configuration_dict['outputProvider']
        # load outputProvider
        tupleLoadProvider = DopUtils.load_provider(output_configuration, self._prov_available)
        if tupleLoadProvider[0].isError():
            return tupleLoadProvider[0]
        self._output_provider = tupleLoadProvider[1]
        
        print("21264; Output provider successfully loaded.")
        return DopError()

    def init_output_provider(self, configuration_dict, session:str ="") -> DopError:
        if self._output_provider is None:
            return DopError(1)
        
        output_configuration: dict = configuration_dict['outputProvider']
        output_confstring: str = output_configuration['configuration']
        
        # data callbacks
        self._output_provider.set_userdata(self)
        self._output_provider.set_on_data_callback(self.data_callback) 
        self._output_provider.set_on_error_callback(self.error_callback)
        self._output_provider.attach_stop_event(self._stopEvent) 
        print("21265; Initializing output provider.")
        # Needed for the dynamic change in session of every client
        output_confstring = output_confstring.replace('%SESSION%', session)
        err: DopError = self._output_provider.init(output_confstring)
        if err.isError(): 
            return err 

        self._output_configured = True
        return DopError()


    def load_configure_output_provider(self, configuration_dict, session:str = "") -> DopError:
       
        err = self.load_output_provider(configuration_dict)
        if err.isError(): 
            return err 
        return self.init_output_provider(configuration_dict, session)

    def load_integrity_provider(self, configuration_dict) -> DopError:
                
        if ('integrity_provider' in configuration_dict) == False:
            return (DopError(21112, 'Configuration value error; integrityProvider key is undefined/missing.'))
      

        integrity_conf: dict = configuration_dict['integrity_provider'] 
        tupleProvider = DopUtils.load_provider(integrity_conf, self._prov_available)

        if tupleProvider[0].isError():
            return tupleProvider[0]
        
        provider = tupleProvider[1]

        self._mle_client.integrity_provider = provider 
        print("21260; Integrity provider loaded.")
        return DopError()
    
    
    def load_encoding_provider(self, configuration_dict) -> DopError:
        
        if ('encoding_provider' in configuration_dict) == False:
            return (DopError(21113, 'Configuration value error; encodingProvider key is undefined/missing.'))

        encoding_conf: dict = configuration_dict['encoding_provider'] 
        
        tupleProvider = DopUtils.load_provider(encoding_conf, self._prov_available)

        if tupleProvider[0].isError():
            return tupleProvider[0]
        
        provider = tupleProvider[1]
        
        self._mle_client.encoding_provider = provider 
        print("21261; Encoding provider loaded.")
        return DopError()



    def load_ciphers_info(self, configuration_dict) -> DopError:
        """
        Reorganizes the configuration information about the encryption providers
        in order to make it easily accessible in a dictionary where the name of the cipher
        is used as a key. The values of the dictionary can be used to load 
        the ciphers dynamically.
        """
        
        if ('crypto_providers' in configuration_dict) == False:
            return (DopError(21118, 'Configuration value error: cryptoProviders key is undefined/missing'))
        

        encryption_info = {}
        for key, value in configuration_dict.items():
            if key == 'crypto_providers':
                for cipher in value: 
                    cipher_path = cipher.get('path')
                    cipher_class = cipher.get('class')
                    encryption_info[cipher.get('name')] = {"path": cipher_path,   \
                     "class": cipher_class, "configuration": ""}

        self._mle_client.encryption_providers_info = encryption_info
        print("21266; Info for crypto providers loaded.")
        return DopError()


    def load_providers(self, configuration_dict: dict) -> DopError:
        """
        This function makes the code in the scripts shorter 
        by loading and configuring both input and output providers.
        Both individual functions and this aggragaye functions way are kept in order to facilitate debugging
        and the usage of either or the other of the providers.
        """
        err = self.load_input_provider(configuration_dict)
        if err.isError():
            return err
        
        err = self.load_output_provider(configuration_dict)
        if err.isError():
            return err


        err = self.load_encoding_provider(configuration_dict)
        if err.isError():
            return err

        err = self.load_integrity_provider(configuration_dict)
        if err.isError():
            return err

        err = self.load_ciphers_info(configuration_dict)
        if err.isError():
            return err

        return DopError()


    def load_mle_providers(self, configuration_dict) -> DopError:
        
        err = self.load_encoding_provider(configuration_dict)
        if err.isError():
            return err

        err = self.load_integrity_provider(configuration_dict)
        if err.isError():
            return err

        err = self.load_ciphers_info(configuration_dict)
        if err.isError():
            return err

        return DopError()

    def open_input_provider(self) -> DopError:
        if self._input_configured: 
            print("21350; Opening input provider")
            err: DopError = self._input_provider.open() 
            if err.isError():
                print(err.msg)
                return err 
            print("21351; Input provider successfully opened")
        else: 
            return DopError(21190, "Input provider not configured")
        
        return DopError() 

    def open_output_provider(self) -> DopError:
        if self._output_configured:
            print("21352; Opening output provider")
            err: DopError = self._output_provider.open()
            if err.isError():
                print(err.msg)
                return err
            print("213523; Output provider successfully opened")
        else: 
            return DopError(21191, "Output provider not configured")
        
        return DopError()


    def close_input_provider(self) -> DopError:
        print("21550; Closing input provider")
        err = self._input_provider.close()
        return err
    
    def close_output_provider(self) -> DopError:
        print("21551; Closing output provider")
        err = self._output_provider.close()
        return err

    def close_providers(self) -> DopError:
        err = self.close_input_provider()
        if err.isError():
            return err

        err = self.close_output_provider()
        if err.isError():
            return err

        return DopError()

    def write(self, msg: str, additional_info: dict = None) -> DopError:
        
        err: DopError = DopError()
        if self._output_provider != None:
            err = self._output_provider.write(msg, additional_info)
        return err
    
    def write_to_endpoint(self, msg: str, endpoint, additional_info: dict = None) -> DopError:
        err: DopError = DopError()
        if self._output_provider != None:
            err = self._output_provider.write_to_endpoint(msg, endpoint, additional_info)
        return err
