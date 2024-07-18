#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

import copy
from typing import Tuple
import json
import base64
import secrets
 
from provider.python.processor.finally_processor_provider import FinallyProcessorProvider
from common.python.error import DopError
from common.python.event import DopEvent, TransportEventHeader, DopEventPayload, DopEventHeader

from common.python.pipeline_memory import PipelineMemory


class EventMultiplicationMLEProcessor(FinallyProcessorProvider):
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = None

        self._providers = None

    def init(self, config: str) -> DopError:
        self._config = config
        return DopError()

    def open(self) -> DopError:
        return DopError()

    def close(self) -> DopError:
        return DopError()


    # on_error
    # on_data
    # userdata
    # init 
    # open
    # close
    # stopEvent 
    # ... 
    def  handle_pipeline_stack(self, pipeline_stack: dict, providers: dict) \
            -> DopError:
        
        """
        Process the contents of pipeline_events: 
        for each property in pipeline_events:
            for each event in pipeline_events.pop(property) : 
                session = event.header.session
                    for each entry in pipeline_data[session]:
                        if session of entry != event.session :
                            event = create new event for that session
                                
                        apply mle on event with details related to that session
                        push event in pipeline_event 
                                
        """
        
        # Providers are : crypto providers, integrity providers and MLE providers
        self._providers = providers
        for event_type in pipeline_stack['events'].properties():
            
            for event in  pipeline_stack['events'].pop(event_type):

                session = event.header.session
                
                # pop the session header as we don't need it anymore
                event_dict_copy = copy.deepcopy(event.to_dict())
                event_dict_copy.pop('session')

                # if session is not in pipeline data, do not propagate event
                for session_with_mle in  pipeline_stack['data'].get(session):
                    session_value = session_with_mle['value']
                                
                    # apply MLE on new event and push event onto pipeline_events 

                    err, mle_event = self._apply_mle(event_dict_copy, session_with_mle)

                    pipeline_stack['events'].push(session_value, mle_event)
                      
        return DopError()


    def _apply_mle(self, event_dict, session_with_mle) -> Tuple[DopError, DopEvent]:
        # string version of event
        event_str = json.dumps(event_dict)

        # MLE data        
        cipher = session_with_mle['cipher_name']
        if cipher == 'none':
            return (DopError(0,"No need to encrypt the message."), self._original_event(event_dict))

        cipher_provider = self._providers['crypto_providers'][cipher.lower()]

        key_b64 = session_with_mle['key']
        mode = session_with_mle['cipher_mode']
        klen = session_with_mle['cipher_keylength']
        encoding = session_with_mle['encoding']
        
        integrity = session_with_mle['integrity_fun']
        integrity_fun = self._providers['integrity_provider'].select_integrity_function(integrity)
        if integrity_fun is None:
            return DopError(24765,f"An error occurred when selecting the integrity function for MLE.\
                Please check if the function {integrity} is supported"), None

        key_b64_bytes = key_b64.encode()
        key = base64.standard_b64decode(key_b64_bytes)

        try: 
            err, mle_event_payload = self.encrypt_and_wrap(
                cipher_provider,
                event_str, 
                {'mode': mode, 'keylength':klen},
                key,
                encoding
            )
            if err.isError():
                return (err, None)
            
            
            digest = integrity_fun(event_str.encode())

            """
            new_event_dict =  {
                'cipher_suite_name' : cipher, 
                'integrity_fun' : integrity,
                'digest' : digest, 
                'mle':1,
                'params': mle_event_payload
            }"""

            new_event_header = TransportEventHeader('',
                            cipher, integrity, digest)
            new_event_header.mle = 1
            new_event = DopEvent(new_event_header, DopEventPayload(mle_event_payload))

            return (DopError(), new_event)


        except Exception as e:
            print(f"Exception: {e}")
           
            return (DopError(24766,"An exception occurred while encapsulating DOP Event in MLE"), 
                   None)


    def _original_event(self, event_dict: dict) -> DopEvent:
        header = DopEventHeader(session="", task = event_dict['task'], DopEvent=event_dict['event'])
        header.mle = 0

        return DopEvent(header, DopEventPayload(event_dict['params']))
    

    
    def encrypt_and_wrap(self, cipher, mess: str, params: dict, key: bytes, encoding: str) -> Tuple[DopError, dict]:
        """Pass the string version of the message to be encrypted, 
        together with the cipher and the configuration parameters. 
        Return the encrypted message inside a wrapper dictionary such as:
        OUT
        {
            "cipher_params": # the input params
                {"mode": params['mode'], 
                "keylength": params['keylength']},
            "iv": iv_b64, 
            "encoding" : encoding,
            "ciphertext" : ciphertext
        }

        This dictionary needs to be inserted into a DopEvent that 
        has a DopTransportHeader
        e.g. {
            "session" : "...",
            "cipher_suite_name" : "...",  # set by the caller of this function
            "integrity_fun":"...",
            "digest":"..."
            "params" : 
                THE OUTPUT OF THIS FUNCTION
            

        }
        """ 
        #   Initialization Vector is always encoded in base64
        iv = secrets.token_bytes(int(cipher.blocksize/8))
        iv_b64_bytes = base64.standard_b64encode(iv)
        iv_b64 = iv_b64_bytes.decode()  # UTF bytes -> str
        
        
        # binary message 
        b_mess = mess.encode()              # str -> bytes
        err, b_ciphertext = cipher.encrypt_bytes(b_mess, params, iv, key)

        if err.isError():
            return (err, {})
        
        # Encoding for interoperability and transmission
        err, encoder_function = self._providers['encoding_provider'].select_encoding(encoding) 
        if err.isError() or encoder_function is None:
            return (err, {})
        
        # encode binary -> text, cross-platform compatible format
        b_encoded_ciphertext = encoder_function(b_ciphertext)
        s_encoded_ciphertext = b_encoded_ciphertext.decode() # UTF bytes -> str


        return (DopError(),{"cipher_params": params,
            "iv": iv_b64, 
            "encoding" : encoding,
            "ciphertext" : s_encoded_ciphertext})
