#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

from typing import Tuple, List
import json

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.rif.model.rif_models import RifPrivateMessage
from common.python.threads import DopStopEvent
from common.python.utils import DopUtils

# PLEASE NOTE that if the subscription is eliminated there is no more any reference to 
# the data recipient that did the subscription; the message can be eliminated via the 'secret' 

class RifPrivateMessageSendProcessor(ProcessorProvider):
    
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = {"rif_private_message_send"}

    
    def init(self, config: str) -> DopError:
        return DopError()
    
    
    def open(self) -> DopError:
        return DopError() 
    
    
    def close(self) -> DopError:
        return DopError() 
    
    
    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) -> DopError:
        """
        rif_private_message_send 
        {
            "session":"",
            "task":"",
            "event":"rif_private_message_send",
            "params":  {
                "auth_token": "",
                "secret": "",
                "subscription_id": "",
                "message": "" 
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
        secret = payload.get('secret', None)
        subscription_id = payload.get('subscription_id', None)
        mess = payload.get('message', None)

        if secret is None or subscription_id is None or mess is None: 
        
            envs.events.push(header.event, DopEvent(
                header, DopEventPayload({ 
                    "err" : DopUtils.ERR_MISS_PARAMS['id'],
                    "phase" : phase
                })))
            return DopError()
        
        # Check subscription exists 
        subscription, perr = db.get_product_subscription(where={'id':subscription_id})
        if perr.isError() or subscription is None:
            # subscription not found
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_SUBSCRIPTION)
            err.perr = perr
            return err
        
        if isinstance(subscription, list):
            subscription = subscription[0]

        # get publisher of product referenced by the subscription
        prod_id = subscription.product
        prods, perr = db.get_product(where= {'id': prod_id})
        if perr.isError() or prods is None: 
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_PRODUCT_NOT_FOUND)
            err.perr = perr 

        if isinstance(prods, list):
            prods = prods[0]


        # Generate lock from secret 
        # Hash of secret
        secret_hash = DopUtils.sha3_256(secret)
        
        priv_mess = RifPrivateMessage(lock = secret_hash, 
                                      subscription_id = subscription_id,
                                      message = mess, 
                                      send_to = prods.get('publisher'))

        _id, perr = db.insert_rif_priv_mess(priv_mess)
        if perr.isError():
            err = DopError(999, "Error in saving private message")
            err.perr = perr 
            return perr 
        
        envs.events.push(header.event, DopEvent(header, DopEventPayload({
            "err": 0, 
            "phase": phase, 
            "lock": secret_hash, 
            "subscription_id" : subscription_id,
            "message" : mess
        })))
        return DopError()
