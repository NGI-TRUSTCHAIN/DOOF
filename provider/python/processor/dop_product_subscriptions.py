#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   author:     Georgiana
#   date:       09/07/2024
#   version:    1.0


from typing import Tuple, List

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.model.models import User 
from common.python.new_processor_env import ProcessorEnvs
from common.python.utils import DopUtils


class DopProductSubscriptionsProcessor(ProcessorProvider): 

    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = "dop_product_subscriptions"

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
        This event is typically emitted by a client. 
        The backend will process this event by emitting an event 
        containing a list of all the subscriptions
        to a product identified by the property 'params.product_id'
        NOTE    that the product_id is the marketplace id of the product

        event: 
        {
            "session":"8abbc354-7258-11e9-a923-1681be663d3e",
            "task":"1",
            "event":"dop_product_subscriptions",
            "params":   {
                            "auth_token":   "890fghja%%432?98",
                            "product_id":   "d1c33f2a-2270-11ea-afdb-080027fdbcfd",
                            "type":         "sub"|"any"
                        }
        }
        """
        if self._event_type == event.header.event:
            return self._handle_dop_product_subscriptions(event, envs)
            
        elif self._event_type in envs.events.properties():
            events = envs.events.pop(self._event_type)
            for ev in events:
                err = self._handle_dop_product_subscriptions(ev, envs)
                if err.isError():
                    return err 
                    
        return DopError() 
    

    def _handle_dop_product_subscriptions(self, event: DopEvent, envs: ProcessorEnvs):

        db = envs.db_provider
        blk = envs.blk_provider
        payload = event.payload.to_dict()
        header = event.header
        session = header.session
        task = header.task
        phase = 1
        
        #   minimum requirements
        product_id = payload.get('product_id',None)
        if product_id is None:
            envs.events.push(header.event, (DopEvent(header, DopEventPayload({
                    "err" : DopUtils.ERR_PROD_REF['id'],
                    "phase" : phase
                }
            ))))
            return DopError()

        # What subset of subscriptions to return? by default, if nothing is specified, any
        # NOTE for ethereum processor, this is not returned by the intermediation provider; 
        # should be computed by processor
        query_t = payload.get('type', 'any') 

        # get authenticated user from stack 
        try:
            user = envs.data.get(User.__name__)[0]
        except:
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            return err

        
        supplicant_addr = user.blk_address
        if supplicant_addr is None:
            envs.events.push(header.event, DopEvent(
                header, DopEventPayload(
                    {"err":DopUtils.ERR_USER_ADDRESS['id'],
                     #"msg": DopUtils.ERR_USER_ADDRESS['msg'],
                    "phase":phase,
                    "product_id" : product_id,
                    "type": query_t
                    })
            ))
            return DopError()


        product_ref, perr = db.get_product_reference(product_id) 
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_PROD_REF)
            err.perr = perr
            return err 
        
        if not product_ref: 
            envs.events.push(header.event, DopEvent(header, 
                            DopEventPayload({
                                "err":DopUtils.ERR_PL_PROD_REF['id'],
                                "phase":phase,
                                "product_id" : product_id,
                                "type": query_t
                            })))
            return DopError()

        prod_addr = product_ref.get('product_blk_address')
        #   get the list of subscriptions to the product from the intermediation platform

        # This query returns all the subscription blk addresses, anything else must be queried separately; 
        # some subscriptions may need to be filtered out 
        perr, subscriptions = blk.productSubscriptions(prod_addr, user.blk_address, user.blk_password)
        
        
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_SUBSCRIPTION)
            err.perr = perr
            return err
        

        # CHECK user == owner of product_id? (to know if I should return subscriber screen) 
        isOwner, perr = db.isOwner(user.id, prod_addr)
    
        whole_visibility = (isOwner or query_t == 'sub')

        updated_subscriptions = []
        for subscription_addr in subscriptions:
            # retrieve from db and from blk info about this subscription;  
            # NOTE table subscription was extended in order to save the blk address 

            subscription = {}
            
            # retrieve info from db 
            info, perr = db.get_additional_info_subscription_addr(subscription_addr)
            info = DopUtils.serialize_datetime(info)
            


            if not perr.isError() and info is not None and len(info) != 0: 
                
                if query_t == 'sub': 
                    # check which subscriptions belong to user  
                    
                    if user.id.lower() != info[0].get('subscriber_id').lower(): 
                        continue

                sid = info[0].pop('id') 
                subscription.update(info[0])
                subscription['subscription_id'] = sid
                if not whole_visibility:
                    subscription.pop('subscriber_screen')
            else:
                # the subscription was not found in the database, skip and
                # don't place this sub in return set
                print(subscription_addr)

            # blk_info product, subscriber, tog, status -- need only tog, status
            perr, blk_info = blk.subscriptionInfo(subscription_addr, user.blk_address, user.blk_password)
            
            if not perr.isError():
                
                prod_blk = blk_info.pop('product')
                # Substitute addr of subscriber with worker id of subscriber 
                subscriber_addr = blk_info.pop('subscriber') 
                
                subscription.update(blk_info)


            updated_subscriptions.append(subscription)

        envs.events.push(header.event, DopEvent(header, DopEventPayload({
            "err" : 0, 
            "phase":phase,
            "product_id": product_id,
            "type": query_t,
            "set": updated_subscriptions
        })))
        return DopError()
            
