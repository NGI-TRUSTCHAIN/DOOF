#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

# version:  1.0
# date:     08/07/2024
# author:   georgiana


import json
from typing import Tuple, List
 
from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.utils import DopUtils, BlockchainEvents as be
from common.python.model.models import Transaction, User

from common.python.model.models import PurposeOfUsage, ProductSubscription


class DopProductSubscribeProcessor(ProcessorProvider):

    def __init__(self):
        super().__init__() 
        self._config = ""
        self._event_type = "dop_product_subscribe"

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
        This events is typically emitted by a client wanting 
        to subscribe to an available product (a product that 
        has been created and manifested on the marketplace). 
        The emitter of the event subscribe has to be authenticated 
        and thus the property auth_token must be valid.

        The subscription can be completed only once the subscriber 
        has selected a purpose of usage for which she wants visibility
        over the data.

        event:
        {
            "session":"8abbc354-7258-11e9-a923-1681be663d3e",
            "task":"1",
            "event":"dop_product_subscribe",
            "params":{
                "auth_token":"hjkhjk456sl$$",
                "purpose_id": "be663d3e-a923-11e9-7258-8abbc3543333", 
                "product_id":"8abbc354-7258-11e9-a923-1681be663d3e"

            }
        }
        """
        if self._event_type == event.header.event: 
            return self._handle_dop_product_subscribe(event, envs)
        
        return DopError()

    

    def _handle_dop_product_subscribe(self, event: DopEvent, envs: ProcessorEnvs):
        
        # Improvement: check if the purpose_id is not already present in the database 
        # for a subscription of the same subscriber to the same product 
        # because otherwise the subscription is done on the blockchain but 
        # is not saved in the database

        blk = envs.blk_provider
        db = envs.db_provider
        payload = event.payload.to_dict()
        header = event.header
        phase = 0
        
        product_id = payload.get('product_id', None)
        if product_id is None:
            envs.events.push(header.event, (DopEvent(header, DopEventPayload({
                    "err" : DopUtils.ERR_MISS_PROD['id'], 
                    "phase" : phase
                }
            ))))
            return DopError()
        
        purpose_id = payload.get('purpose_id', None)
        if purpose_id is None: 
            envs.events.push(header.event, (DopEvent(header, DopEventPayload({
                    "err" : DopUtils.ERR_MISS_PURPOSE['id'], 
                    "phase" : phase
                }
            ))))
            return DopError()


        # get authenticated user from stack 
        try:
            user = envs.data.get(User.__name__)[0]
        except:
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            return err
            

        if not user.blk_address:
            return self._output_error(header, DopUtils.ERR_USER_ADDRESS, phase, envs)
            

        products, perr = db.get_product({'id': product_id})


        if perr.isError(): 
            # NOTE provider err means that there were some infrastructural problems; 
            # Create a specific error and set the provider error (perr)
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_PRODUCT_NOT_FOUND)
            err.perr = err
            # NOTE:  Do not insert anything in events cache as the error will be eventified   
            return err

        if len(products) == 0:
            # NOTE this is an application-layer error
            return self._output_error(header, 
                                      DopUtils.ERR_PL_PRODUCT_NOT_FOUND, 
                                      phase, envs)
           
        
        product = products[0]
        if not product.get('blk_address'):
            # NOTE this is an application-layer error
            return self._output_error(header, DopUtils.ERR_PRODUCT_ADDR_NOT_FOUND,
                                      phase, envs)
            
        #  SUBSCRIBER DATA
        subscriber_id = user.id

         
        pou, perr = db.get_purpose_of_usage(where={"id": purpose_id})

        if perr.isError():
            # infrastructural error
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_SUB) 
            err.perr = perr
            return err
            
        if pou is None:
            # errore applicativo
            return self._output_error(header, 
                                        DopUtils.ERR_GENERIC, 
                                        phase, envs)

        elif isinstance(pou, list):
            pou = pou[0]
        
        
        if subscriber_id != pou.get('subscriber'):
            # You are trying to subscribe with a purpose which is not yours
            return self._output_error(header, 
                                      DopUtils.ERR_GENERIC,
                                      phase, envs)

        

        ### INFO FOR SUBSCRIPTION 
        ## BLK SUBSCRIPTION 
        subscriber_addr = user.blk_address
        secret = user.blk_password
        product_addr = product.get('blk_address') 

        subscription_id = str(DopUtils.create_uuid()) 
        
        perr, sid_address = blk.marketplaceAddress(subscription_id)

        perr, transaction_hash = blk.subscriptionCreate(
                subscription_id,        #   application layer address of the new subscription
                product_addr,
                subscriber_addr,
                secret
        )

        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_IP_SUB)
            err.perr = perr 
            return err
        
        # In the params saved into database, I need the data 
        # to be used in ProductSubscription
        data = json.dumps({ 
            "subscriber_id" : user.id, 
            "subscription_id" : subscription_id, 
            "subscription_address" : sid_address,
            "purpose_id" : purpose_id,
            "product_id": product_id,         
            "secret" : secret,
            "original_session": event.header.session
        })

        transaction = Transaction(
            hash=transaction_hash, 
            event_name=self._event_type,
            client=user.id,  
            task = header.task,
            params=data
        )

        perr = db.create_transaction(transaction)
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_TRANSACT_SAVE)
            err.perr = perr
            return err

        envs.data.push(Transaction.__name__, transaction)

        event_params = {
            "err": 0,
            "phase": phase,
            "purpose_id" : purpose_id,
            "product_id" : product_id,
            "subscription_id": subscription_id
        }
        envs.events.push(header.event, DopEvent(
                    header, DopEventPayload(event_params)
        ))
        

        return DopError()

    def _output_error(self, header, content: dict, phase, envs: ProcessorEnvs) \
        -> DopError:

        envs.events.push(header.event, DopEvent(header, DopEventPayload({
                "err": content['id'], 
                "phase": phase           
        })))

        return DopError()
    