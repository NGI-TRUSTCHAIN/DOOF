#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

from typing import Tuple, List
import json

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.model.models import User
from common.python.rif.model.rif_models import RifPrivateMessage
from common.python.rif.model.rif_schemas import RifPrivateMessageSchema
from common.python.threads import DopStopEvent
from common.python.utils import DopUtils


class RifPrivateMessageListProcessor(ProcessorProvider):
    
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = {"rif_private_message_list"}

    
    def init(self, config: str) -> DopError:
        return DopError()
    
    
    def open(self) -> DopError:
        return DopError() 
    
    
    def close(self) -> DopError:
        return DopError() 
    
    
    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) -> DopError:
        """
        rif_private_message_list 
        {
            "session":"",
            "task":"",
            "event":"rif_private_message_list",
            "params":  {
                "auth_token": ""
            }
        }     
        """
        
        if event.header.event in self._event_type:
           
            out = self._handle_event(event, envs)
            # NOTE if there is an error, the processing is interrupted and 
            # any other events left in the stack are emptied by the worker
            if out.isError():
                return out 
            
        return DopError()
    
    def _handle_event(self, event: DopEvent, envs: ProcessorEnvs) -> DopError:
        
        db = envs.db_provider
        blk = envs.blk_provider
        payload = event.payload.to_dict() 
        header = event.header
        phase = 1

        # get authenticated user from stack 
        try:
            user: User = envs.data.get(User.__name__)[0]
        except:
            perr =  DopError(999, "missing data from pipeline data stack")
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            err.perr = perr 
            return err
        
        
        #messages, perr = db.get_mess_for_user(user.id)
        messages, perr = db.get_mess_with_info_for_user(user.id)
        if perr.isError():
            err = DopError(888, "Could not retrieve private messages")
            err.perr = err 
            return err 

        
        #if isinstance(messages, RifPrivateMessage):
        #    messages = [messages]
        #schema = RifPrivateMessageSchema(many=True)
        #messages = schema.dump(messages)

        messages = DopUtils.serialize_datetime(messages)

        envs.events.push(header.event, DopEvent(
            header, DopEventPayload(
                {
                    "err" : 0, 
                    "phase" : phase, 
                    "private_messages": messages
                }
            )
        ))

        return DopError()
