#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   version:    1.1
#   author:     Georgiana
#   date:       09/07/2024

#   Ver 1.1
#   - Secret is publisher's address  

#   Ver 1.0
#   - support for multi-proxy: proxy dictionary within list brackets 
#   - support for processor macros: configurable values
#   - channel
#   - pub configuration JSON is base64 encoded

import json
from typing import Tuple, List

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload 
from common.python.new_processor_env import ProcessorEnvs
from common.python.utils import DopUtils 
from common.python.model.models import User

class DopPubConfigurationProcessor(ProcessorProvider):

    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = "dop_pub_configuration"  

    def init(self, config: str) -> DopError:
       
        # default_config = "proxy_addr=10.8.0.3;proxy_port=2783;gp=@GRACE_PERIOD;
        # kma=@KEY_MAXAGE;kimc=@KEY_INVALIC_MC;swg=@START_WITH_GET;"
                
        # config= "proxy_addr=127.0.0.1;proxy_port=3000;gp=3000;kma=20;kimc=15;swg=true;loop_interval=5000"
        self._config = config

        err, conf_dict = DopUtils.config_to_dict(config)
        t, self.PROXY_ADDR = DopUtils.config_get_string(conf_dict, ["proxy_addr"], "10.8.0.3")
        t, self.PROXY_PORT = DopUtils.config_get_string(conf_dict, ["proxy_port"], "2783")
        t, self.GRACE_PERIOD = DopUtils.config_get_string(conf_dict, ["gp"], "@GRACE_PERIOD")
        t, self.LOOP_INTERVAL = DopUtils.config_get_string(conf_dict, ["loop_interval"], 5000)
        try: 
            # GRACE PERIOD can be int or a default string macro
            # int: 4000
            self.GRACE_PERIOD = int(self.GRACE_PERIOD)
        except:
            pass 

        t, self.KEY_MAXAGE = DopUtils.config_get_string(conf_dict, ["kma"], "@KEY_MAXAGE")
        try:
            # KEY_MAXAGE can be int or a default string macro
            # int = 20
            self.KEY_MAXAGE = int(self.KEY_MAXAGE)
        except:
            pass                                          

        try: 
            self.LOOP_INTERVAL = int(self.LOOP_INTERVAL)
        except: 
            pass                               
                   
        t, self.KEY_INVALID_MC =  DopUtils.config_get_string(conf_dict, ["kimc"], "@KEY_INVALID_MC")
        try:
            # KEY_INVALID_MC can be int or a default string macro
            # int = 15
            self.KEY_INVALID_MC = int(self.KEY_INVALID_MC)
        except:
            pass                                          
        
        t, self.START_WITH_GET = DopUtils.config_get_string(conf_dict, ["swg"], "@START_WITH_GET") 
        if self.START_WITH_GET.lower() == 'true':
            self.START_WITH_GET = True
        elif self.START_WITH_GET.lower() == 'false':
            self.START_WITH_GET = False

        return DopError()

    def open(self) -> DopError:
        return DopError()

    def close(self) -> DopError:
        return DopError()

    
    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) \
        -> DopError:
    
        """
        This event is typically emitted by a client on behalf of the publisher 
        wanting to know the configuration information for initiating a dopified data stream. 
        The backend will process this event by emitting an event, dop_publisher_config, 
        which holds the json configuration needed for configuring the product in the dop stack. 
        The client emitting this event MUST BE authenticated and thus the 
        auth_token must be valid.
        {
            'session': ...,
            'task': ...,
            'event': 'dop_pub_configuration',
            'params': {
                'auth_token' : ...,
                'product_id' : "8abbc354-7258-11e9-a923-1681be663d3e"
            }
        }

        """
    
        """
        OUTPUT (params)
        {
        "err": 0, 
        "phase": 1,
        "product_id" : "8abbc354-7258-11e9-a923-1681be663d3e",
        "config": {"channel":"8abbc354-7258-11e9-a923-1681be663d3e",
        "publisher":
            {"password":"2a749bc6de62441aca4a",
            "secret":"3491d233b8dbde90ef8a",
            "product":"0xf11f5804575fdE0CA15035d3F735C92a1370b569"},
        "server":
           [{"address":"10.8.0.3","port":"2783"}],
        "grace_period":3000,
        "key_maxage":20,"
        key_len":48,
        "key_invalid_maxcount":10,
        "loop_interval":5000,
        "start_with_get":true,
        "log_level":1}
        }
        """

        if self._event_type == event.header.event:
            return self._handle_dop_pub_configuration(event, envs)
        
        return DopError()


    def _handle_dop_pub_configuration(self, event: DopEvent, envs: ProcessorEnvs) \
        -> DopError:

        db = envs.db_provider
        blk = envs.blk_provider
        payload = event.payload.to_dict()
        header = event.header
        
        phase = 1

        if not "product_id" in payload: 
            envs.events.push(header.event, DopEvent(
                header, DopEventPayload({
                    "err" : DopUtils.ERR_MISS_PROD['id'],
                    "phase": phase
                })
            ))
            return DopError()

        product_id = payload.get('product_id')

        # get authenticated user from stack 
        try:
            user = envs.data.get(User.__name__)[0]
        except:
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            return err


        if not user.blk_address: 
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                    "err" : DopUtils.ERR_USER_ADDRESS['id'],
                    #"msg" : DopUtils.ERR_USER_ADDRESS['msg'],
                    "phase": phase,
                    "product_id" : product_id
            })))
            return DopError()
        

        # Get the product details for checks and then for reply event
        det_product, perr = db.get_product_details(product_id)
        if perr.isError() or len(det_product) == 0:
            err = DopError()
            err.perr = perr
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                    "err": DopUtils.ERR_PL_PRODUCT_NOT_FOUND['id'],
                    #"msg": DopUtils.ERR_PL_PRODUCT_NOT_FOUND['msg'],
                    "phase": phase,
                    "product_id" : product_id
            })))
            return err

        
        # Check that the user is the publisher of the product
        if det_product.get('publisher_username') != user.username: 
            # user is not the publisher
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                    "err": DopUtils.ERR_PL_NOT_AUTHORIZED['id'],
                    #"msg": DopUtils.ERR_PL_NOT_AUTHORIZED['msg'],
                    "phase": phase,
                    "product_id" : product_id
            })))
            return DopError()     


        if not det_product.get('blk_address'):
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                    "err" : DopUtils.ERR_PRODUCT_ADDR_NOT_FOUND['id'],
                    #"msg": DopUtils.ERR_PRODUCT_ADDR_NOT_FOUND['msg'],
                    "phase": phase, 
                    "product_id" : product_id
            })))
            return DopError()

        product_address = det_product.get('blk_address')

        # Create event params to return
        config =  {"channel": product_id,
            "publisher":{
                "password":user.blk_password,
                "secret": user.blk_address, 
                "product":product_address},
            "server": [{
                "address": self.PROXY_ADDR,
                "port":self.PROXY_PORT}],
            "grace_period":self.GRACE_PERIOD,
            "key_maxage":self.KEY_MAXAGE,
            "key_len":48,
            "key_invalid_maxcount":self.KEY_INVALID_MC,
            "loop_interval":self.LOOP_INTERVAL,
            "start_with_get":self.START_WITH_GET,
            "log_level":3,
            "ks_watchdog_maxtime": 4000,
            "kg_watchdog_maxtime": 4000
            }
        
        
        config_str = json.dumps(config)
        config_b64, err = DopUtils.to_base64(config_str)


        out_payload = DopEventPayload({
            "err":0,
            "phase":phase,
            "product_id" : product_id,
            "config": config_b64
        })


        envs.events.push(header.event, DopEvent(header,
            out_payload))
        return DopError()
        