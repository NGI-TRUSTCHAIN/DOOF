#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

# date:         10/07/2025
# author:       georgiana
# version:      1.0



from typing import Tuple, List

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.utils import DopUtils
from common.python.model.models import User

class DopSubscriptionInfoProcessor(ProcessorProvider):

    def __init__(self):
        super().__init__() 
        self._config = ""
        self._event_type = "dop_subscription_info"

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
        The event handled is typically emitted by a client which wants to retrieve 
        information about a subscription from the intermediation platform, 
        enriched with information from the persistence layer as well. 
        This information contains, e.g., the purpose of the subscription, the grant status, credit and debit. 
        The emitter has to be authenticated and thus the property auth_token has to be valid.
        

        imperative event:
        {
            "session":"8abbc354-7258-11e9-a923-1681be663d3e",
            "task":"1",
            "event":"dop_subscription_info",
            "params":{
                "subscription_id":"8abbc777-7258-1100-a923-1681be663d3e",
                "auth_token":"hjkhjk456sl$$"
            }
        }
        """    
    
        blk = envs.blk_provider
        db = envs.db_provider
        payload = event.payload.to_dict() 
        header = event.header
        phase = 1

        new_header = DopEventHeader(header.session, header.task, self._event_type)
        
        if not 'subscription_id' in payload: 
            envs.events.push(new_header.event, DopEvent(
                new_header, DopEventPayload({
                    "err": DopUtils.ERR_MISS_SUBSCRIPTION['id'],
                    "phase": phase             
                    } 
                )
            ))
            return DopError()

        subscription_id = payload.get('subscription_id')

        # get authenticated user from stack 
        try:
            user = envs.data.get(User.__name__)[0]
        except:
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            return err

        user_address = user.blk_address         # needed for the supplicant information
        if not user_address:
            err = DopUtils.create_dop_error(DopUtils.ERR_USER_ADDRESS)
            envs.events.push(new_header.event, DopEvent(new_header, DopEventPayload({
                    "err" : DopUtils.ERR_USER_ADDRESS['id'],
                    #"msg": DopUtils.ERR_USER_ADDRESS['msg'],
                    "subscription_id" : subscription_id,
                    "phase": phase
                }
            )))
            return DopError()
                    
        
        # blk_info contains: product, subscriber, tog, status
        # previously (bh): blk_address, subscriber, status, credit, debit, usage, last_charge and tog
        perr, subscription_addr = blk.marketplaceAddress(subscription_id)
        if perr.isError():            
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_SUBSCRIPTION)
            err.perr = perr        
            return err
        
        perr, blk_info = blk.subscriptionInfo(subscription_addr, user_address, user.blk_password)
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_IP_SUBSCRIPTION)
            err.perr = perr
            return err 

        if blk_info is None or len(blk_info) == 0:
            envs.events.push(new_header.event, DopEvent(new_header, DopEventPayload({   
                "err": DopUtils.ERR_IP_SUBSCRIPTION['id'],
                "subscription_id": subscription_id,
                "phase": phase,
                "info" : {}
            })))
            return err


        db_info, perr = db.get_product_subscription_no_secret({'id': subscription_id})
        # id, subscriber, product_id, purpose_id, created_at, username(subscriber_name), name (subscriber_screen), purpose_label  
        
        if perr.isError() or db_info is None:
            # subscription not found
            err = DopError()
            err.perr = perr
            return err

        if db_info is None or len(db_info) == 0:
            envs.events.push(new_header.event, DopEvent(new_header, DopEventPayload({   
                "err": DopUtils.ERR_PL_SUBSCRIPTION['id'],
                #"msg":  DopUtils.ERR_PL_SUBSCRIPTION['msg'],
                "subscription_id": subscription_id,
                "phase": phase,
                "info" : {}         # here I could use only the data coming from the intermediation platform
            })))
            return DopError()
    
        db_info = db_info[0]
        
        # Not needed in notification
        sub_addr = blk_info.pop('subscriber')
        prod_addr = blk_info.pop('product')

        is_owner, perr = db.isOwner(user.id, prod_addr)
        
        sub_id = db_info['subscriber_id']
        is_subscriber = (sub_id == user.id)

        whole_information = is_owner or is_subscriber

        

        if whole_information:
            blk_info['subscriber_screen'] = db_info['subscriber_screen']
        blk_info['purpose_url'] = db_info['purpose_url']
        blk_info['purpose_label'] = db_info['purpose_label']
        blk_info['purpose_id'] = db_info['purpose_id']
        blk_info['product_id'] = db_info['product_id']
        blk_info['subscriber_id'] = db_info['subscriber_id']
        blk_info['created_at'] = db_info['created_at'].isoformat()
        

        envs.events.push(new_header.event, DopEvent(new_header, DopEventPayload(
            {
                "err" : 0,
                "subscription_id" : subscription_id,
                "phase" : phase, 
                "info": blk_info
            }
        )))
        return  DopError()
