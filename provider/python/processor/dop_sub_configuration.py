#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   version:    1.0
#   author:     Georgiana
#   date:       16/04/2024


import json 

from typing import Tuple, List

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload 
from common.python.new_processor_env import ProcessorEnvs
from common.python.utils import DopUtils 
from common.python.model.models import User

class DopSubConfigurationProcessor(ProcessorProvider):

    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = "dop_sub_configuration"

    def init(self, config: str) -> DopError:
        # default_config = "proxy_addr=10.8.0.3w;proxy_port=2783;"
        # config= "proxy_addr=127.0.0.1;proxy_port=3000;"
        self._config = config
              
        err, conf_dict = DopUtils.config_to_dict(config)
        t, self.PROXY_ADDR = DopUtils.config_get_string(conf_dict, ["proxy_addr"], "10.8.0.3")
        t, self.PROXY_PORT = DopUtils.config_get_string(conf_dict, ["proxy_port"], "3000")
        return DopError()

    def open(self) -> DopError:
        return DopError()

    def close(self) -> DopError:
        return DopError()

    #@DopUtils.auth_required()
    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) \
            -> DopError:

        """
        This event is typically emitted by a client on behalf of the subscriber with respect to 
        a specific subscription, wanting to know the configuration information for receiving a
        dopified data stream and dedopifying it if granted. 
        The backend will process this event by emitting a notification, dop_sub_configuration, 
        which holds the json configuration needed for configuring the subscription in the 
        DVCO sub stack. 
        The client emitting this event MUST be authenticated and thus the 
        auth_token must be valid.
        {
            'session': 'b6ac9d17-1eef-4538-a923-f353ee8d6e13',
            'task': 3,
            'event': 'dop_sub_configuration',
            'params': {
            	'auth_token': '725666916942423990a8c352f3a2de17',
            	'subscription_id': '2B92323A-436A-11EA-8359-08002776D00D'
            }
        }

        """
        """
        OUTPUT
        {
        "err": 0, 
        "phase": 1,
        "
        "config":
        {"channel": "8BB1DFC8-E207-428A-8E2E-7D0F44AF2DF5",
        "keymaxage":600,
        "gcperiod":60,
        "log_level":3,
        "chillout":10,
        "subscriber":{
            "address":"7BFRSQJYAK2ERNGJWC2SKDEP5PAN6PRTENSSU6GDS5U3LPJP6VE6GWKO4A",
            "secret":"YXJjdGljIHNwaWNlIGxpemFyZCBjcnVuY2ggcmVzb3VyY2UgZmluZ2VyIHNpZWdlIHN1cnZleSBoZWFsdGggY2VudHVyeSBicmF2ZSB3YWxudXQgYW5ub3VuY2Ugd29ydGggaGFsZiBtaWRuaWdodCBjYXRhbG9nIHBsYXN0aWMgYWR2YW5jZSB1cHNldCBlcnJvciBvbmxpbmUgaG9tZSBhYnN0cmFjdCB1cG9u",
            "subscription": "2B92323A-436A-11EA-8359-08002776D00D" 
            },
        "server":{"address":"10.8.0.3","port":"2783"}
        }
        }
        
        Please note that the config parameter can also be a base64 encoded string (the stringified version
        of the same json)
        """
    
        if self._event_type == event.header.event:
            return self._handle_dop_sub_configuration(event, envs)
        
        return DopError()
    
    def _handle_dop_sub_configuration(self, event: DopEvent, envs: ProcessorEnvs) \
            -> DopError:
        db = envs.db_provider
        blk = envs.blk_provider
        payload = event.payload.to_dict()
        header = event.header
        phase = 1
        
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

    
        
        user_id = user.id
        user_address = user.blk_address
        if not user_address:
            # application layer error
            envs.events.push(header.event, DopEvent(
                header, DopEventPayload(
                    {"err":DopUtils.ERR_USER_ADDRESS['id'],
                     "phase": phase,
                     "subscription_id" : subscription_id
                    })
            ))
            return DopError()

        # The where clause ensures that the user requesting this information
        # is the subscriber to which the subscription belongs
        subscription, perr = db.get_product_subscription(
                                where={"id": subscription_id,
                                        "subscriber" : user_id})

        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_SUBSCRIPTION)
            err.perr = perr        
            return err
        if subscription is None:
            envs.events.push(header.event, DopEvent(header, 
                                DopEventPayload({
                                        "err": DopUtils.ERR_PL_SUBSCRIPTION_NOT_FOUND['id'],
                                        "phase": phase,
                                        "subscription_id" : subscription_id                                       
                                    })))
            return DopError()
        

        perr, subscription_addr = blk.marketplaceAddress(subscription_id)
        if perr.isError():            
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_SUBSCRIPTION)
            err.perr = perr        
            return err
        

        config = {
                "channel" : subscription.product,
                "server":{
                    "address":self.PROXY_ADDR,
                    "port":self.PROXY_PORT
                },
                "keymaxage":600,
                "gcperiod":60,
                "log_level":3,
                "chillout":10,
                "watchdogPeriod":5000,
                "subscriber":{
                    "address": user_address,
                    "secret": subscription.subscriber_secret,
                    "subscription" : subscription_addr
                    }
        }

        config_str = json.dumps(config)
        config_b64, err = DopUtils.to_base64(config_str)

        out_payload = DopEventPayload({
                "err": 0, 
                "phase":phase, 
                "subscription_id" : subscription_id,
                "config": config_b64
                })

        envs.events.push(header.event, 
                DopEvent(header, out_payload)) 
        return DopError()
