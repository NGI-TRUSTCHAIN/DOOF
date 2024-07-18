#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

# version:  1.0
# date:     04/07/2024
# author:   georgiana

from typing import Tuple, List

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload 
from common.python.model.schemas import ProductSchema
from common.python.model.models import User, ProductSubscription
from common.python.model.schemas import ProductSubscriptionSchema

from common.python.new_processor_env import ProcessorEnvs
from common.python.utils import DopUtils 


class DopProductsListProcessor(ProcessorProvider):

    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = DopEvent.DOP_PRODUCTS_LIST

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
        containing a list of products available from the marketplace. 
        The client emitting this event MUST BE authenticated and thus the 
        auth_token must be valid. By setting the property set it is 
        possible to, for instance, instantiate a result set (query) 
        containing all the published products, or only the products that 
        belong to the emitter (identified by the property auth_token). 
        Please see set for more details.

        :param event:
        :param envs: A class with the properties used as arguments
                     by all the processors
        event: 
        {
            "task":"1",
            "event":"dop_products_list",
            "params":   {
                            "set_range":    {"from":"0", "to":"50"},
                            "type": "all"|"other"|"published"|"subscribed",
                            "filter": { 'id': ''},
                            "auth_token":   "890fghja%%432?98"
                        }
        }
        """

        if self._event_type == event.header.event:
            return self._handle_dop_products_list(event, envs)
            
        elif self._event_type in envs.events.properties():
            # This processor is used in the pipeline in a point that it not the "entry" point of the 
            # processing  
            to_process = envs.events.pop(self._event_type) 
            for ev in to_process : 
                out = self._handle_dop_products_list(ev, envs)
                # NOTE if there is an error, the processing is interrupted and 
                # any other events left in the stack are emptied by the worker
                if out.isError():
                    return out 
            
    
        return DopError()

     
    
    def _handle_dop_products_list(self, event: DopEvent, envs: ProcessorEnvs) \
            -> DopError:
        
        db = envs.db_provider
        blk = envs.blk_provider
        payload = event.payload.to_dict() 
        header = event.header

        phase = 1
        
        
        filter = payload.get('filter', None)
        pagination = payload.get('set_range',  {"from":"-1", "to":"-1"})
        fr = int(pagination.get('from',-1))  # offset
        to = int(pagination.get('to',-1))    # limit is to - fr + 1
        
        if fr != -1 and to != -1:
            limit = to - fr + 1
        else:
            limit = -1

        # type of query: all, published, other, set

        type_q = payload.get("set", None)
        if type_q is None: 
            type_q = payload.get("type", None)


        # get authenticated user from stack 
        try:
            user = envs.data.get(User.__name__)[0]
        except:
            #perr =  DopError(999, "missing data from pipeline data stack")
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            #err.perr = perr 
            return err
    

        if type_q is None or type_q == '': 
            type_q="all"       

        if not (filter.get('id', None) and len(filter.values()) == 1):
            if type_q == "published" or type_q == "subscribed":
                products, perr = db.get_sets_products(user.id, subset= {"set":type_q}, where=filter) 
            
            elif type_q == "other":
                products, perr =  db.get_other_products(user.id, where = filter) 

            elif type_q == 'all':
                products, perr = db.get_all_products(where = filter, limit = limit, offset = fr)

            else: 
                envs.events.push(header.event, DopEvent(header, DopEventPayload({
                    "err" : DopUtils.ERR_TYPE['id'],
                    "phase": phase
                })))
                return DopError()

                
        else: 
            # FILTER: ONLY ID 
            # Get a detailed product with all the attributes
            is_subscriber = False
            products_subscriber = None
           

            products, perr = db.get_product_summary(filter.get('id'))
            
            if perr.isError():
                err = DopUtils.create_dop_error(DopUtils.ERR_PL_PROD_QUERY)
                err.perr = perr 
                return err 
            if products is None:
                envs.events.push(event.header, DopEvent(
                    header, DopEventPayload({
                        "err":DopUtils.ERR_PL_PROD_QUERY['id'],
                        "phase": phase,
                        "type": type_q, 
                        "filter": filter
                    })
                )) 
                return DopError()

 

        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_PROD_QUERY)
            err.perr = perr
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                "err" :  DopUtils.ERR_PL_PROD_QUERY['id'], 
                #"msg": DopUtils.ERR_PL_PROD_QUERY['msg'],
                "phase": phase,
                "type": type_q, 
                "filter": filter          
            })))
            return err

        products = DopUtils.serialize_datetime(products)

        
        if not isinstance(products, list):
            
            product = products
            if 'blk_address' in product:
                product.pop('blk_address')

            results = [product]
        else:
            results = []
            for product in products:

                mkt_product = product
                if 'blk_address' in mkt_product:
                    mkt_product.pop('blk_address')
                    
                results.append(mkt_product)
    
        envs.events.push(header.event, DopEvent(header,
                    DopEventPayload({
                        "err": 0, 
                        "filter" : filter, 
                        "phase": phase,
                        "type": type_q, 
                        "set": results
                }))) 
        return DopError()

