#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   date:       12/07/2024 
#   author:     georgiana
#   version:    1.0 

import json
from typing import Tuple, List

from provider.python.processor.provider_processor import ProcessorProvider 

from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.model.models import ProductSubscription, Transaction, User
from common.python.new_processor_env import ProcessorEnvs
from common.python.utils import DopUtils,  BlockchainEvents as be


class DopSubscriptionRevokeProcessor(ProcessorProvider):

    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = "dop_subscription_revoke"

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
        event:
        {
            "session": "8abbc354-7258-11e9-a923-1681be663d3e",
            "task": "1",
            "event": "dop_subscription_revoke",
            "params": {
                "subscription_id":"8abbc354-7258-11e9-a923",
                "auth_token":"hjkhjk456sl$$"
            }
        }
        """

        if self._event_type == event.header.event:
            return self._handle_dop_subscription_revoke(event, envs)
        
        return DopError()


    def _handle_dop_subscription_revoke(self, event: DopEvent, envs: ProcessorEnvs) -> DopError:
        
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

        # PUBLISHER
        
        # get authenticated user from stack 
        try:
            publisher = envs.data.get(User.__name__)[0]
        except:
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            return err
        

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
                    "subscription_id" : subscription_id
            })))
            return DopError()

        product = products[0]
        product_address = product.get('blk_address')
        
        # SUBSCRIBER (if we want to notify change of status)
        subscriber_id = subscription.subscriber   
        subscriber, perr = db.get_user({"id": subscriber_id})   
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            err.perr = perr
            return err
        if subscriber is None: 
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                    "err" : DopUtils.ERR_PL_USER_NOT_FOUND['id'],
                    "phase": phase,
                    "subscription_id" : subscription_id  
            })))
            return DopError()

        # CHECK AUTHORIZATION  
        publisher_id = publisher.id
        publisher_address = publisher.blk_address
        publisher_password = publisher.blk_password
        if not publisher_address:
            # Happens when the user was not enabled on the intermediation platform 
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                    "err" : DopUtils.ERR_USER_ADDRESS['id'],
                    "phase": phase,
                    "subscription_id" : subscription_id  
            })))
            return DopError()
        
        is_owner, perr = db.isOwner(publisher_id, product_address)
        if not is_owner:
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                                "err":DopUtils.ERR_PL_NOT_AUTHORIZED['id'],
                                "phase": phase,
                                "subscription_id" : subscription_id  
                            })))
            return DopError()

        # ALL GOOD, Revoke
        
        perr, tx_hash = blk.subscriptionRevoke(subscription.blk_address, publisher.blk_password)

        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_IP_GRANT)
            err.perr = perr
            return err
        
        data = {
            "subscription_id": subscription_id,
            "subscription_address" : subscription.blk_address,
            "original_session": event.header.session
        }

        transaction = Transaction(
            hash=str(tx_hash),
            event_name=self._event_type,
            client=publisher_id,
            task=header.task,
            params = json.dumps(data)
        ) 
        
        perr = db.create_transaction(transaction)
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_DEPOSIT)
            err.perr = perr
            return err

        # NOTIFY PHASE 0
        envs.events.push(header.event, 
            DopEvent(header, DopEventPayload({
                "err":0, 
                "phase": phase,
                "subscription_id" : subscription_id 
            }))
        ) 
        
        return DopError()
    