#   SPDX-License-Identifier: Apache-2.0

#   version:     1.0
#   author:      Georgiana
#   date:        10/04/2024

import json
from typing import Tuple, List
 
from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.utils import DopUtils, BlockchainEvents as be


class DopRecipientSetProcessor(ProcessorProvider):
   
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_types = {"dop_recipient_set", "dop_enable_identity"}

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
        This processor creates a new account recipient for the indicated identity. The emitter of the event 
        must be a sysadmin. 
                
        event:
        {
            "session":"8abbc354-7258-11e9-a923-1681be663d3e",
            "task":"1",
            "event":"dop_recipient_set",
            "params":   {
                            "auth_token": "890fghja%%432?98",
                            "subject": "john.red@example.com",
                            "recipient":"example/john"
			}
        }

        The processor can also be used as part of the pipeline for dop_enable_identity event, 
        after the processor for dop_enable_identity, in order to add the recipient indicated in the 
        given event, if present.
        {
            "session":"8abbc354-7258-11e9-a923-1681be663d3e",
            "task":"1",
            "event":"dop_enable_identity",
            "params":   {
                            "auth_token" : "888ghj=89l;#", 
                            "subject": "john.red@example.com",
                            "screen_name" : "name",
                            "recipient":"example/john"
                        }
        } 
        """


        if event.header.event in self._event_types:
            
            return self._handle_event(event, envs)

        return DopError()    
    
 
    def _handle_event(self, event, envs) -> DopError:
        
        blk = envs.blk_provider
        db = envs.db_provider
        logger = envs.logger_provider 
        data_stack = envs.data

        phase = 1 

        header = event.header
        payload = event.payload.to_dict()
        

        session = header.session
        task = header.task

    
        token = payload.get('auth_token')
        subject = payload.get('subject')
        recipient = payload.get('recipient', None)

        if recipient is None:
            return DopError()        

        # Use some information that was placed on the data stack by auth check
        try:
            user = envs.data.get('user')[0]
        except: 
            perr =  DopError(999, "missing data from pipeline data stack") 
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            err.perr = perr 
            return err
        
        if not user.is_admin:
            event_payload = DopEventPayload({
                    'err': DopUtils.ERR_OP_NOT_PERMITTED['id'],
                    #'msg': DopUtils.ERR_OP_NOT_PERMITTED['msg'],
                    "phase": phase
            })
            envs.events.push(header.event, DopEvent(header, event_payload))
            return DopError()


        user, perr = db.get_user_from_username(subject) 
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            err.perr = perr
            return err 
        
        if user is None: 
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                    "err" : DopUtils.ERR_PL_USER_NOT_FOUND['id'],
                    #"msg": DopUtils.ERR_PL_USER_NOT_FOUND['msg'],
                    "phase": phase
            })))
            return DopError()


        # UPDATE RECIPIENT ENTRY IN DB (update account)
        user.recipient = recipient 
        perr = db.update_user(user)
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_UPDATE['id'])
            err.perr = perr
            return err


        event_payload = DopEventPayload({
                "err": 0, 
                "phase": phase,
                "subject": subject, 
                "recipient" : recipient
        })
        envs.events.push(header.event, DopEvent(header, event_payload))
        return DopError()