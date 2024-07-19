#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   ver:    1.0
#   date:   9/07/2024
#   author: georgiana



from typing import Tuple, List
import json

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.model.models import User
from common.python.rif.model.rif_models import RifAdvertisementInterest
from common.python.threads import DopStopEvent
from common.python.utils import DopUtils


class RifAdvertisementInterestProcessor(ProcessorProvider):
    
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = {"rif_advertisement_interest"}

    
    def init(self, config: str) -> DopError:
        return DopError()
    
    
    def open(self) -> DopError:
        return DopError() 
    
    
    def close(self) -> DopError:
        return DopError() 
    
    
    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) -> DopError:
        """
        rif_advertisement_interest 
        {
            "session":"",
            "task":"",
            "event":"rif_advertisement_interest",
            "params":  {
                "auth_token": "",
                "accept": "",
                "ads_id": "",
                "purpose_id": "",
                "product_id": ""
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


        # Payload params 
        accept = payload.get("accept", None) 
        # The values for accept: 
        # - True, true, 1, t 
        # - False, false, 0, f
        ads_id = payload.get("ads_id", None)
        product_id = payload.get("product_id", None)

        if accept is None or ads_id is None or product_id is None:
            envs.events.push(header.event, DopEvent(
                header, DopEventPayload({ 
                    "err" : DopUtils.ERR_MISS_PARAMS['id'],
                    "phase" : phase
                })))
            return DopError()


        if accept in {"True", "t", "true", 1, True}:
            accept = True 
        elif accept in {"False", "f", "false", 0, True}:
            accept = False 
        else: 
            envs.events.push(header.event, DopEvent(
                header, DopEventPayload({ 
                    "err" : 996, # Accept values are not known 
                    "phase" : phase
                })))
            return DopError()


        # Not mandatory if 'accept' if False 
        purpose_id = payload.get("purpose_id", None)
        if accept == True and purpose_id is None :
            envs.events.push(header.event, DopEvent(
                header, DopEventPayload({ 
                    "err" : DopUtils.ERR_MISS_PARAMS['id'],
                    "phase" : phase
                })))
            return DopError()

 
        # Checks on product: is the user owner of product?
        products, perr = db.get_product({'id': product_id})
        
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_PRODUCT_NOT_FOUND)
            err.perr = perr
            return err
        if len(products) == 0:
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                    "err" : DopUtils.ERR_PL_PRODUCT_NOT_FOUND['id'],
                    "phase": phase,
                    "product_id" : product_id
            })))
            return DopError()

        product = products[0]
        is_owner = (product.get('publisher') == user.id)  

        if not is_owner:
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                                "err":DopUtils.ERR_PL_NOT_AUTHORIZED['id'],
                                "phase": phase,
                                "product_id": product_id 
                            })))
            return DopError()
        
        
        interest = RifAdvertisementInterest(
            account_id = user.id, 
            advertisement_id = ads_id, 
            accept = accept, 
            product_id = product_id
            )
        
        _id, perr = db.insert_rif_advert_interest(interest)
        if perr.isError(): 
            err = DopError(987, "Error in saving user's interest in ad")
            err.perr = perr 
            return err 
        if _id is None: 
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                "err" : 987,
                "phase" : phase, 
                "accept": accept,
                "ads_id": ads_id,
                "purpose_id": purpose_id,
                "product_id": product_id
            })))
            return DopError(987)

        # If everything went well, add the interest object into the data stack to be used by 
        # next processor(s), if any  
        
        envs.data.push(RifAdvertisementInterest.__name__, interest)

        envs.events.push(header.event, DopEvent(header, DopEventPayload({
                "err" : 0,
                "phase" : phase, 
                "accept": accept,
                "ads_id": ads_id,
                "purpose_id": purpose_id,
                "product_id": product_id
        })))

        return DopError()
