#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   ver:    1.0
#   date:   12/07/2024
#   author: georgiana


from typing import Tuple, List
import json

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.model.models import User
from common.python.rif.model.rif_models import RifSubscriptionNews
from common.python.threads import DopStopEvent
from common.python.utils import DopUtils


class RifNewsListProcessor(ProcessorProvider):
    
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = {"rif_news_list"}

    
    def init(self, config: str) -> DopError:
        return DopError()
    
    
    def open(self) -> DopError:
        return DopError() 
    
    
    def close(self) -> DopError:
        return DopError() 
    
    
    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) -> DopError:
        """
        rif_news_list 
        {
            "session":"",
            "task":"",
            "event":"rif_news_list",
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
            user = envs.data.get(User.__name__)[0]
        except:
            #perr =  DopError(999, "missing data from pipeline data stack")
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            #err.perr = perr 
            return err
        

        news, perr = db.get_rif_sub_news_info(user.id)


        if perr.isError(): 
            err = DopError(987, "Error while retrieving notifications for user. ")
            err.perr = perr 
            return err 
        
        if news is None: 
            envs.events.push(header.event, DopEvent(header, 
                        DopEventPayload({
                            "err" : 987,
                            "phase" : phase
                        })))
        ser_news = DopUtils.serialize_datetime(news) 
        envs.events.push(header.event, DopEvent(header, 
                        DopEventPayload({
                            "err" : 0,
                            "phase" : phase,
                            "notifications" : ser_news
                        })))

        return DopError()
