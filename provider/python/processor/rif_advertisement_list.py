#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   ver:    1.0
#   date:   5/06/2024
#   author: georgiana



from typing import Tuple, List
import json

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.rif.model.rif_models import RifAdvertisement
from common.python.threads import DopStopEvent
from common.python.utils import DopUtils

from common.python.model.models import User

class RifAdvertisementListProcessor(ProcessorProvider):
    
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = {"rif_advertisement_list"}

    
    def init(self, config: str) -> DopError:
        return DopError()
    
    
    def open(self) -> DopError:
        return DopError() 
    
    
    def close(self) -> DopError:
        return DopError() 
    
    
    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) -> DopError:
        """
        rif_advertisement_list 
        {
            "session":"",
            "task":"",
            "event":"rif_advertisement_list",
            "params":  {
                "auth_token": "",
                "filter": "other"
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

        """
        In the output event include (from rif_advertisement table): 
        •	Ads_id
        •	Description
        •	Purpose_id
        •	Company_id / partner_id 
        •	Created_at
        Moreover, include the following details from purpose and account table: 
        •	Purpose_url
        •	Purpose_label
        •	Company_name
         
        """
        db = envs.db_provider
        blk = envs.blk_provider
        payload = event.payload.to_dict() 
        header = event.header
        phase = 1

        # get authenticated user from stack 
        try:
            user = envs.data.get(User.__name__)[0]
        except:
            perr =  DopError(999, "missing data from pipeline data stack")
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            err.perr = perr 
            return err

        # Payload params 
        filt = payload.get('filter')
        if filt != 'other':
            envs.events.push(header.event, DopEvent(header, 
                            DopEventPayload({
                                    "err" : 998, #operation not supported
                                    "phase" : phase
                                })))
            return DopError()

        # get the list of advertisements to which the user has not expressed anything
        ads_list, perr = db.get_ads_for_user(user.id)
        if perr.isError():
            err = DopError(997, "Error when retrieving the advertisements for the given user")
            err.perr = err 
            return err 
        
        if ads_list is None:
            envs.events.push(header.event, DopEvent(header, 
                        DopEventPayload({
                                "err" : 997,
                                "phase" : phase
                            })))
            return DopError()
        
        ads_list = DopUtils.serialize_datetime(ads_list)

        notification_payload = DopEventPayload({
                "err": 0, 
                "phase":phase,
                "filter" : filt,
                "ads_list" : ads_list

        }) 

        envs.events.push(header.event, DopEvent(header, notification_payload))
        return DopError()
