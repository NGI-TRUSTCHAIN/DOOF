#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   ver:    1.0
#   date:   4/07/2024
#   author: georgiana

from typing import Tuple, List
import json

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.threads import DopStopEvent
from common.python.utils import DopUtils
from common.python.model.models import User

class RifActionableProductsProcessor(ProcessorProvider):
    
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = {"rif_actionable_products"}

    
    def init(self, config: str) -> DopError:
        return DopError()
    
    
    def open(self) -> DopError:
        return DopError() 
    
    
    def close(self) -> DopError:
        return DopError() 
    
    
    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) -> DopError:
        """
        rif_actionable_products 
        {
            "session":"",
            "task":"",
            "event":"rif_actionable_products",
            "params":  {
                "auth_token": "",
                "ads_id": ""
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
            #perr =  DopError(999, "missing data from pipeline data stack")
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            #err.perr = perr 
            return err

        # Get info from event 
        # PAYLOAD PARAMS
        ads_id = payload.get('ads_id', None)
        if ads_id is None:
            
            envs.events.push(header.event, DopEvent(
                header, DopEventPayload({ 
                    "err" : DopUtils.ERR_MISS_PARAMS['id'],
                    "phase" : phase
                })))
            return DopError()
    

        prods, perr = db.get_actionable_products(user.id, ads_id)
        
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_PROD_QUERY)
            err.perr = perr 
            return err 
        
        if prods is None:
                envs.events.push(event.header, DopEvent(
                    header, DopEventPayload({
                        "err":DopUtils.ERR_PL_PROD_QUERY['id'],
                        "phase": phase,
                        "ads_id" : ads_id
                    })
                )) 
                return DopError()
        
        prods = DopUtils.serialize_datetime(prods)
        
        notification_payload = DopEventPayload({
            "err":0,
            "phase":1,
            "ads_id" : ads_id,
            "products" : prods
        })

        envs.events.push(header.event, DopEvent(header, notification_payload))
        return DopError()
