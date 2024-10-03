#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   version:    1.0
#   author:     georgiana
#   date:       09/07/2024  

import binascii
from typing import Tuple, List
import json

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.model.models import ProductSubscription
from common.python.new_processor_env import ProcessorEnvs

from common.python.utils import DopUtils

""" 
{"session": "-", 
"task": "-", 
"event": "event_set",
"params":
     {"transaction_id": "0x553587c44bc1b82d14520a7b829eefb9fb0d67fa922f03ac4c0b30b3aa6f778c", 
    "event_set": [{"event_id": "LogSubscriptionCreate", "data":
    ["0x00000000000000000000000030b3a485adbcc958b8a14a65fb6cf60a53117f8c",
    "0x167345ae7f86f3f54dd4b62c985382139dacf79fe65d065df9300fffded52583", 
    "0x0000000000000000000000000000000000000000000000000000000000000000"]}]}}}
"""

class LogSubscriptionCreateProcessor(ProcessorProvider): 
    
    EVENT_SET = "event_set"
    TRANSACTION_ID = "transaction_id"
    EVENT_ID = "event_id"

    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = {"event_set", "events_set"}
        self._event_id_content = "LogSubscriptionCreate"
        self._trigger_event = "dop_subscription_create"

        # Variables to be used by processing logic
        self._db_trans = None 

    
    def init(self, config: str) -> DopError:
        self._config = config
        return DopError()

    def open(self) -> DopError:
        return DopError()

    def close(self) -> DopError:
        return DopError()

    
    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) \
            -> DopError:
        

        if event.header.event not in self._event_type:
            return DopError() 
        
        err = DopError()

        
        db = envs.db_provider
        blk = envs.blk_provider
        phase = 1

        payload = event.payload.to_dict()
        
        blk_events = payload.get(self.EVENT_SET) # NOTE assume 1 event
        transaction_id = payload.get(self.TRANSACTION_ID)

        # take operation type from the transaction info saved in db
        # linked to this transaction_id 
            
        # retrieve transaction entry from database
        db_trans, perr = db.get_transaction(where={'hash' : transaction_id})
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_TRANSACT_NOT_FOUND)
            err.perr = perr 
            return err 
        if db_trans is None: 
            return DopError(0, "nothing to do, transaction not found")

        # create event header based on event_name, client and task from db_trans
        event_label = db_trans.event_name       # process event if this = trigger event; build notification for given event type
        
        # NOTE iterate through the set of events and check each one of them: 
        # event_id, data
        to_proc = []
        for blk_ev in blk_events: 
            ev_id = blk_ev[self.EVENT_ID]
            
            if ev_id != self._event_id_content:
                # only process here events of type "LogSubscriptionCreate"
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

        

        # Db transaction contents 
        
        account_id = db_trans.client                # build notification for given client (send on all active sessions)
        task =  db_trans.task                   # for notification header
        
        # User to be notified of success/failure of operation
        user, perr = envs.db_provider.get_user(where={'id':account_id})
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            err.perr = perr
            return err 
        
        if user is None: 
            return DopError()
    

        session, perr = envs.db_provider.get_session({'client': account_id})
        if isinstance(session, list):
            session = session[0]        #take one session (the first one)

        
        event_header = DopEventHeader(session=session.value, 
                                      task = task,
                                      DopEvent=event_label)

        # DB TRANSACTION INFO 
        data = json.loads(db_trans.params) 
        original_session = data.pop("original_session", None)

        # HERE STARTS THE LOGIC TO COMPLETE SUBSCRIPTION 
        
        sid_blk_addr = data.get('subscription_address')     # cross-check with event_trans
        subscriber_id = data.get('subscriber_id')
        subscription_id = data.get('subscription_id')       
        purpose_id = data.get('purpose_id')                
        product_id = data.get('product_id')               
        secret = data.get('secret')

        # NOTE some more checks 
        
        proc = to_proc[0]
        log_data = proc.get('data')
        log_blk_address = log_data[1].lower()
        log_err = log_data[2]
        

        # check if blk address of subscription is included in the log being handled
        # and the given log does not contain an error  

        delete = False

        #e.g. sid_blk_addr = data.get('subscription_address')  #"0x1140321b08161d63244f961720bbe72a5459df54a3183ada3d547c627a1395b4"
        #e.g. log_blk_addr="0x1140321b08161d63244f961720bbe72a5459df54a3183ada3d547c627a1395b4"
        if log_err[0:2] == '0x':
            err_b = binascii.unhexlify(log_err[2:])
            err_i = int.from_bytes(err_b,"big")
        else: 
            # NOTE always assume hex encoding, with or without 0x
            err_b = binascii.unhexlify(log_err)
            err_i = int.from_bytes(err_b,"big")
        
        if err_i != 0 and err_i != 1:
            print("Log error")
            # errs : 100 - 106
            # delete transaction, notify supplicant user of result 
            delete = True 
                

        if sid_blk_addr.lower() != log_blk_address: 
            # NOTE should not happen, if transaction hash / id was saved correctly 
            print("not the same subscription")
            # delete transaction, notify supplicant of result 
            delete = True

        
        if delete:
            
            # delete transaction
            perr = db.delete_transaction(transaction_id) 
            if perr.isError():
                # if there is an error when deleting transaction, 
                # everything is rolled back 
                err = DopUtils.create_dop_error(DopUtils.ERR_PL_TRANSACT_DEL)
                err.perr = perr
                return err     

            params =   {
                "phase": phase, 
                "err" : 1,
                "log_err": err_i,       #     I may also use the last 4 hex digits received from monitor
                "subscription_id" : subscription_id,
                "purpose_id": purpose_id,
                "product_id": product_id,
                "original_session" : original_session
            }
            
        
            output_event = DopEvent(event_header, 
                        DopEventPayload(params))
            
            self._user_notification(output_event, envs)

            envs.events.push(event_header.event, output_event)

            return DopError()

        # else continue operations 

        # return to creation of subscription 
        

        subscription = ProductSubscription(
            id = subscription_id, 
            subscriber = subscriber_id, 
            subscriber_secret = secret, 
            product = product_id,
            purpose_id = purpose_id
            , blk_address = sid_blk_addr
        )
        id, perr = db.create_product_subscription(subscription) 
        
        
        envs.data.push(ProductSubscription.__name__, subscription)

        if perr.isError():
            # Infrastructural error
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_SUB)
            err.perr = perr
            return err

        # after saving the subscription in the database, delete transaction
        perr = db.delete_transaction(transaction_id) 
        if perr.isError():
            # if there is an error when deleting transaction, 
            # everything is rolled back 
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_TRANSACT_DEL)
            err.perr = perr
            return err         
        


        payload = DopEventPayload({
            "err":0,
            "phase" : phase,
            "original_session" : original_session,
            "subscription_id": subscription_id,
            "purpose_id": purpose_id,
            "product_id": product_id,
           
        })
         
        # RETURN EVENT

        output_event = DopEvent(event_header, payload)

        self._user_notification(output_event, envs)

        envs.events.push(event_header.event, output_event)

        return err

    
    def _user_notification(self, event, envs) -> DopError:
        # This method prepares the data needed for notifying the result of the 
        # operation to the other interested party (published/subscriber)
        from provider.python.processor.find_sessions_mle_processor import FindSessionsMLEProcessor
        processor = FindSessionsMLEProcessor()
        # this processor can be configured to send the event on all the active sessions 
        processor.init("multiple_sessions=true;")
        err = processor.handle_event(event, envs)
        return err
    
    