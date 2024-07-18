#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

# version:  1.0
# date:     15/07/2024
# author:   georgiana


import json
from typing import Tuple, List
 
from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.utils import DopUtils, BlockchainEvents as be
from common.python.model.models import Transaction, User



class DopProductUnsubscribeProcessor(ProcessorProvider):

    def __init__(self):
        super().__init__() 
        self._config = ""
        self._event_type = "dop_product_unsubscribe"

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
        This events is typically emitted by a client wanting to unsubscribe 
        from a subscription (a product that the emitter has subscribed to 
        indicating a data processing usage). 
        The emitter of the event unsubscribe has to be authenticated and thus 
        the property auth_token must be valid.

        event:
        {
            "session":"8abbc354-7258-11e9-a923-1681be663d3e",
            "task":"1",
            "event":"dop_product_unsubscribe",
            "params":{
                "auth_token":"hjkhjk456sl$$",
                "subscription_id" : "c6f81768-bc62-45ea-9981-78cd34ee1468"

            }
        }
        """
        if self._event_type == event.header.event: 
            return self._handle_dop_product_unsubscribe(event, envs)
        
        return DopError()

    

    def _handle_dop_product_unsubscribe(self, event: DopEvent, envs: ProcessorEnvs):
        

        blk = envs.blk_provider
        db = envs.db_provider
        payload = event.payload.to_dict()
        header = event.header
        phase = 0
        
        
        if not 'subscription_id' in payload: 
            envs.events.push(header.event, DopEvent(
                header, DopEventPayload({
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
            

        if not user.blk_address:
            
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                    "err": DopUtils.ERR_USER_ADDRESS['id'], 
                    "phase": phase           
            })))
            return DopError()
            
        
        # SUBSCRIPTION         
        subscription, perr = db.get_product_subscription({"id": subscription_id})
        if perr.isError():
            # infrastructural error
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_SUBSCRIPTION_NOT_FOUND)
            err.perr = perr
            return err
        if subscription is None: 
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                    "err" : DopUtils.ERR_PL_SUBSCRIPTION_NOT_FOUND['id'],
                    "phase": phase,
                    "subscription_id" : subscription_id  
            })))
            return DopError()


        # CHECK THAT USER IS INDEED SUBSCRIBER 
        if subscription.subscriber != user.id:
            envs.events.push(header.event,DopEvent(header, DopEventPayload({
                    "err" : DopUtils.ERR_OP_NOT_PERMITTED['id'],
                    "phase": phase,
                    "subscription_id" : subscription_id
            })))
            return DopError()
        

        product_id = subscription.product
        products, perr = db.get_product({'id': product_id})
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_PRODUCT_NOT_FOUND)
            err.perr = perr
            return err
        if len(products) == 0:
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                    "err" : DopUtils.ERR_PL_PRODUCT_NOT_FOUND['id'],
                    "phase": phase,
                    "subscription_id": subscription_id, 
                    "product_id" : product_id  
            })))
            return DopError()

        product = products[0]
        if not product.get('blk_address'):
            err = DopUtils.create_dop_error(DopUtils.ERR_PRODUCT_ADDR_NOT_FOUND)
            envs.events.push(header.event,
                              DopEvent(header, DopEventPayload({
                                        "err": DopUtils.ERR_PRODUCT_ADDR_NOT_FOUND['id'],
                                        "phase" : phase,
                                        "subscription_id": subscription_id, 
                                        "product_id": product_id
                                        })))
            return DopError()

        
        subscription_addr = subscription.blk_address
        product_address = product.get('blk_address') 

        subscriber_address = user.blk_address
        subscriber_id = user.id
        subscriber_pass = user.blk_password

        #transaction_hash, perr = blk.product_unsubscribe(
        #    subscription_id,
        #    subscriber_address,
        #    subscriber_pass,
        #    product_address
        #    )
        perr, transaction_hash = blk.subscriptionDelete(
            subscription_addr, 
            product_address,
            subscriber_address, 
            subscriber_pass
        )

        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_IP_UNSUB)
            err.perr = perr
            return err
        
        data = json.dumps({"subscription_id": subscription_id,
                           "subscription_address" : subscription_addr,
                           "product_id": product_id, 
                           "original_session": event.header.session
                           })
        
        transaction = Transaction(
            hash=transaction_hash, 
            event_name=self._event_type,
            client=user.id, 
            task = header.task,
            params = data
        )

        perr = db.create_transaction(transaction)
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_TRANSACT_SAVE)
            err.perr = perr
            return err


        envs.events.push(header.event, DopEvent(
                    header, DopEventPayload({
                        "err": 0,
                        "phase": phase,
                        "subscription_id": subscription_id,
                        "product_id" : product_id
                    })))


        
        return DopError()
