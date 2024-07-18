#   SPDX-License-Identifier: Apache-2.0
#   © Copyright Ecosteer 2024

from typing import Tuple, List
import json

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.threads import DopStopEvent
from common.python.utils import DopUtils
from common.python.model.models import User


class DexChangeScreenProcessor(ProcessorProvider):
    
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = {"dex_change_screen"}

    
    def init(self, config: str) -> DopError:
        return DopError()
    
    
    def open(self) -> DopError:
        return DopError() 
    
    
    def close(self) -> DopError:
        return DopError() 
    
    
    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) -> DopError:
        """
        dex_change_screen 
        {
            "session":"",
            "task":"",
            "event":"dex_change_screen",
            "params":  {
                "auth_token": "",
                "new_screen_name" :""
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
        
        blk = envs.blk_provider
        db = envs.db_provider
        logger = envs.logger_provider 
        phase = 1 

        header = event.header
        payload = event.payload.to_dict()
        
        nsn = payload.get('new_screen_name', None)

        if nsn is None:
            envs.events.push(header.event, DopEvent(header, DopEventPayload(
                {
                    "err": 1,
                    "phase": phase,
                    "new_screen_name": nsn
                }
            )))
            return DopError()

        # get authenticated user from stack 
        try:
            user = envs.data.get(User.__name__)[0]
        except:
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND) 
            return err

        
        user.name = nsn 
        perr = db.update_user(user)
        if perr.isError():
            err = DopUtils.create_dop_error(879,"Error while updating screen name")
            err.perr = perr 
            return err 
        
        envs.events.push(header.event, DopEvent(header, DopEventPayload(
            {
                "err": 0,
                "phase": phase,
                "new_screen_name": nsn
            }
        )))
        

        return DopError()
