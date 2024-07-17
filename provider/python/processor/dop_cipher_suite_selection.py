#   SPDX-License-Identifier: Apache-2.0
#   © Copyright Ecosteer 2024

import base64
from typing import Tuple, List

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.model.models import Session, EncryptedSession
from common.python.model.schemas import EncryptedSessionSchema
from common.python.utils import DopUtils



class DopCipherSuiteSelectionProcessor(ProcessorProvider):

    
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = "dop_cipher_suite_selection"

    def init(self, config: str) -> DopError:
        self._config = config
        return DopError()

    def open(self) -> DopError:
        return DopError()

    def close(self) -> DopError:
        return DopError()

    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) \
            -> DopError:
        """
        This event is typically emitted by a client wanting to start an
        encrypted session with the back-end. 
        This requests is needs to be authenticated, thus the properties 
        session and auth_token need to be in the database and valid.

        event:
        {
            "session":"8abbc354-7258-11e9-a923-1681be663d3e",
            "task":"1",
            "event":"dop_cipher_suite_selection",
            "params":   {
                            "auth_token": "890fghja%%432?98",
                            "cipher_suite":{"name":"none","mode":"none","keylength":"0"}
                   	        "cipher_key":"" 
			}
        }

        """ 
    
        if self._event_type == event.header.event:
            return self._handle_css(event, envs)
        return DopError()    
    

    def _handle_css(self, event, envs) -> DopError:

        db = envs.db_provider
        crypto_tools = envs.crypto_providers

        params = event.payload.to_dict()
        header = event.header
        session = header.session
        task = header.task
        phase = 1

        token = params.get("auth_token")
        cipher_suite = params.get("cipher_suite")
        key_b64 = params.get("cipher_key")


        supported_ciphersuites = []
        for tool in crypto_tools:
            cipher = crypto_tools[tool]
            
            capabilities = cipher.capabilities()

            supported_ciphersuites.extend(capabilities)

        
        if not cipher_suite in supported_ciphersuites:
            err = DopError(DopUtils.ERR_CIPHER_SUITE['id'], DopUtils.ERR_CIPHER_SUITE['msg'])
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                    "err": DopUtils.ERR_CIPHER_SUITE['id'], 
                    "phase" : phase
                
            })))
            return DopError()
            
        # Key length
        c_kl_bytes = int(int(cipher_suite['keylength'])/8)
        key_b64_bytes = key_b64.encode()    # get the bytes representation 
        key = base64.standard_b64decode(key_b64_bytes) # decode from b64

        if c_kl_bytes != len(key):
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                    "err" : DopUtils.ERR_LEN_KEY['id'],
                    "phase" : phase
            })))
            return DopError()

        # get the session id
        session_obj_w_id, perr = db.get_session({'value':session, 'token':token})
        if perr.isError() :
            # Infrastructural error, sinche the presence of the session in the DB was checked by 
            # auth macro shortly before this processor
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_SESSION_NOT_FOUND)
            err.perr = perr 
            return err
        
        if session_obj_w_id is None:
            envs.events.push(header.event, DopEvent(header,
                                DopEventPayload({
                                    "err":    DopUtils.ERR_PL_SESSION_NOT_FOUND['id'],
                                    "phase": phase
                                })))
            return DopError()
        
        session_id = session_obj_w_id.id
        # Preprocess db info as to not insert emtpy/0 vals, else it is not possible to update them
        mode = cipher_suite['mode'] if cipher_suite['mode']  else 'none' # do not insert empty values in db
        keylen = int(cipher_suite['keylength']) if int(cipher_suite['keylength']) else '-1' # do not insert 0
        db_key = key_b64 if key_b64 else 'none'

        # create the new EncryptedSession object
        encrypted_session_obj = EncryptedSession(
            session_id = session_id,
            cipher_name = cipher_suite['name'],
            cipher_mode = mode,
            cipher_keylength = keylen,  #in bits (then it must be divided by 8)
            key = db_key,               # key is saved in the database in a textual format
            encoding = 'base64',
            integrity_fun = 'crc16'
        )

        
        perr = db.update_encrypted_session(session_id,**EncryptedSessionSchema().dump(encrypted_session_obj))
        if perr.isError():
            # infrastructural error
            err = DopError(DopUtils.ERR_PL_ENC_SESSION_NOT_CREATED['id'], DopUtils.ERR_PL_ENC_SESSION_NOT_CREATED['msg']) 
            err.perr = perr
            return err

 
        envs.events.push(header.event,(DopEvent(header, 
                       DopEventPayload({
                            "err" : 0,
                            "phase": phase
                        }))))
        
        return DopError()
