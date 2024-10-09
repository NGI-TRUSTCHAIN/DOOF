#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   ver:    1.0
#   date:   11/07/2024
#   author: georgiana

from typing import Tuple, List
import json

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.model.models import ProductSubscription
from common.python.rif.model.rif_models import RifSubscriptionNews
from common.python.threads import DopStopEvent
from common.python.utils import DopUtils


class RifNewsAddProcessor(ProcessorProvider):
    
    EVENT_SET = "event_set"
    TRANSACTION_ID = "transaction_id"
    EVENT_ID = "event_id"
    
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = {
            "event_set"
            }

        self._transact_op = {
            "LogSubscriptionCreate":1,
            "LogSubscriptionDelete":2
        }
        
        self._event_id_content =  {
            "LogSubscriptionCreate",
            "LogSubscriptionDelete"
        }
    
    def init(self, config: str) -> DopError:
        return DopError()
    
    
    def open(self) -> DopError:
        return DopError() 
    
    
    def close(self) -> DopError:
        return DopError() 
    
    
    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) -> DopError:
        """
        The input event is a event_set, notifying the worker of the completion of an operation.  
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
        
        # retrieve transaction from event payload
        blk_events = payload.get(self.EVENT_SET) # NOTE assume 1 event
        if blk_events is None:
            return DopError()
        transaction_id = payload.get(self.TRANSACTION_ID)

        to_proc = []
        for blk_ev in blk_events: 
            ev_id = blk_ev[self.EVENT_ID]
            
            if ev_id not in self._event_id_content:
                # only process here events of type LogSubscriptionCreate/LogSubscriptionDelete
                continue 

            data = blk_ev['data']
            if len(data) == 0:
                # NOTE does this ever happen?
                continue
            
            # SUBSTRING MARKETPLACE ADDRESS TO ONLY PROCESS RELEVANT LOGS
            # blk.contract_address = '0x30b3A485AdBCc958b8a14A65fb6CF60a53117f8C'
            if blk.contract_address[0:2] == '0x' or blk.contract_address[0:2] == '0X':
                this_mkt = blk.contract_address[2:].lower()
            else:
                this_mkt = blk.contract_address.lower()
            
            
            #E.G. data[0] = '0x00000000000000000000000030b3a485adbcc958b8a14a65fb6cf60a53117f8c'
            trans_mkt = data[0].lower()
            if this_mkt not in trans_mkt: 
                # the check could also be: 
                # l = len(this_mkt)
                # subs = trans_mkt[len(trans_mkt) - l:] #30b3a485adbcc958b8a14a65fb6cf60a53117f8c
                # if this_mkt == subs:
                print("Received log from another marketplace.")  
                continue 
            

            to_proc.append(blk_ev)
        
        if len(to_proc) == 0:
            return DopError()
        

        if len(to_proc) > 1: 
            # Q: Does this ever happen?
            print("Multiple pieces of info in 1 log event.")

        for p in to_proc: 
            try: 
                ps = envs.data.get(ProductSubscription.__name__)[0]
            except: 
                err =  DopError(999, "missing data from pipeline data stack")
                return err
            
            product, perr = db.get_product_summary(ps.product)
            if perr.isError() or product is None:
                err = DopUtils.create_dop_error(DopUtils.ERR_PL_PROD_QUERY)
                err.perr = perr 
                return err 

            ev_id = p[self.EVENT_ID]
            if ev_id in {'LogSubscriptionCreate', 
                            'LogSubscriptionDelete'}:
                supplicant_id = ps.subscriber 

            elif ev_id in {'LogSubscriptionGranted', 'LogSubscriptionRevoked'}:
                supplicant_id = product.get('publisher')

            sub_news = RifSubscriptionNews(
                subscription_id= ps.id,
                product_id = ps.product, 
                supplicant_id = supplicant_id, # determined based on publisher or subscriber, 
                purpose_id = ps.purpose_id,
                action = self._transact_op[ev_id],
                send_to = product.get('publisher') # owner of product
            )

            _id, perr = db.insert_rif_subscription_news(sub_news)

            if perr.isError():
                return perr 
            

        return DopError()
