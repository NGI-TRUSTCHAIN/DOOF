#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   ver:    1.0
#   date:   4/06/2024
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

class RifAdvertisementCreateProcessor(ProcessorProvider):
    
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = {"rif_advertisement_create"}

    
    def init(self, config: str) -> DopError:
        return DopError()
    
    
    def open(self) -> DopError:
        return DopError() 
    
    
    def close(self) -> DopError:
        return DopError() 
    
    
    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) -> DopError:
        """
        Recipient_ads_id is under the responsibility of the data recipient
        rif_advertisement_create 
        {
            "session":"",
            "task":"",
            "event":"rif_advertisement_create",
            "params":  {
                "auth_token": "",
                "secret": "",
                "description": "",
                "purpose_id": "",
                "recipient_ads_id": ""
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

        # PAYLOAD PARAMS
        purpose_id = payload.get("purpose_id", None) 
        secret = payload.get("secret", None)
        rec_ads_id = payload.get("recipient_ads_id", None)
        description = payload.get("description", None)

        if purpose_id is None or \
            secret is None or \
                description is None or\
                    rec_ads_id is None:
            
            envs.events.push(header.event, DopEvent(
                header, DopEventPayload({ 
                    "err" : DopUtils.ERR_MISS_PARAMS['id'],
                    "phase" : phase
                })))
            return DopError()


        # get authenticated user from stack 
        try:
            user = envs.data.get(User.__name__)[0]
        except:
            #perr =  DopError(999, "missing data from pipeline data stack")
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            #err.perr = perr 
            return err

        # check if purpose id exists in db 
        pou, perr  = db.get_purpose_of_usage(where = {'id': purpose_id})
        if perr.isError():
            err =  DopUtils.create_dop_error(DopUtils.ERR_PL_PURPOSE_NOT_FOUND)
            err.perr = perr 
            return err 
        
        if pou is None:
            envs.events.push(header.event, DopEvent(header, 
                            DopEventPayload({
                                    "err" : DopUtils.ERR_PL_PURPOSE_NOT_FOUND['id'],
                                    "phase" : phase, 
                                    "purpose_id": purpose_id
                                })))
            return DopError()
        


        # Hash of secret
        secret_hash = DopUtils.sha3_256(secret)


        advert = RifAdvertisement(
            ads_lock = secret_hash,
            description = description, 
            purpose_id = purpose_id,
            partner_id = user.id, 
            recipient_ads_id = rec_ads_id    
        )


        _id, perr = db.insert_rif_advertisement(advert)
        if perr.isError() or _id is None:
            err = DopUtils.create_dop_error(DopUtils.ERR_GENERIC)
            err.perr = perr 
            return err 
        
        event_payload = DopEventPayload({
            "err": 0, 
            "phase" : phase,
            "ads_lock" : secret_hash, 
            "purpose_id" : purpose_id, 
            "description" : description,
            "recipient_ads_id" : rec_ads_id,
            "id" : _id
            })

        envs.events.push(header.event, DopEvent(header, event_payload))
        return DopError()
    
