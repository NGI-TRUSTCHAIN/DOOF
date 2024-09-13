#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   ver:    1.0
#   date:   14/06/2024
#   author: georgiana


import copy
import json
import threading


from common.python.error import DopError
from common.python.utils import DopUtils 
from common.python.threads import DopStopEvent

from components.clients.python.doof_python_apis import DOOFPythonAPIs 
import rif_events 

class RifPythonAPIs(DOOFPythonAPIs):
    def __init__(self):
        super().__init__()

        self._subscribe_sync = threading.Event()
        self._subscribe_sync.clear()


    
    def init(self, conf_file) -> DopError:
        err = super().init(conf_file)
        if err.isError(): 
            return err 
        
        self._app_protocol.set_userdata(self)
        self._app_protocol.set_on_dop_product_subscribe(
            self.dop_product_subscribe_handler
            )
        return DopError()

    @property 
    def subscribe_sync(self):
        return self._subscribe_sync

    def dop_product_subscribe_handler(self, message_topic, message_payload, userdata):
        ud: RifPythonAPIs = userdata 
        ud.tracefun("dop_product_subscribe_handler")
        ud.tracemsg(message_topic)
        ud.tracemsg(f"@REPLY{message_payload}")
        with ud.event_received_lock:
            ud.last_events_received[ud._label_dop_product_subscribe] = message_payload 

        ud.subscribe_sync.set()

    def rif_advertisement_create(self, secret:str, description:str, purpose_id:str, rec_ads_id: str, task=""):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
         
        ev = copy.deepcopy(rif_events.rif_advertisement_create)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        # info specific for event
        ev['params']['secret'] = secret 
        ev['params']['description'] = description 
        ev['params']['purpose_id'] = purpose_id 
        ev['params']['recipient_ads_id'] = rec_ads_id
        # send event
        request = f"@JSON;{json.dumps(ev)}"
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        print(err)
        return err 
    
    def rif_advertisement_list(self, task=''):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
         
        ev = copy.deepcopy(rif_events.rif_advertisement_list)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token
        
        # send event
        request = f"@JSON;{json.dumps(ev)}"
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        print(err)
        return err


    def rif_advertisement_interest(self, accept:bool, ads_id:str, purpose_id: str, product_id: str, task=''):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
         
        ev = copy.deepcopy(rif_events.rif_advertisement_interest)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token
        
        # info specific for event
        ev['params']['accept'] = accept 
        ev['params']['ads_id'] = ads_id
        ev['params']['purpose_id'] = purpose_id
        ev['params']['product_id'] = product_id

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        print(err)
        return err

    
    def rif_actionable_products(self, ads_id:str, task=''):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
         
        ev = copy.deepcopy(rif_events.rif_actionable_products)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token
        
        # info specific for event
        ev['params']['ads_id'] = ads_id


        # send event
        request = f"@JSON;{json.dumps(ev)}"
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        print(err)
        return err


    def rif_private_message_send(self, secret:str, subscription_id:str, message: str, task=''):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
         
        ev = copy.deepcopy(rif_events.rif_private_message_send)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token
        
        # info specific for event
        ev['params']['secret'] = secret
        ev['params']['subscription_id'] = subscription_id
        ev['params']['message'] = message

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        print(err)
        return err 

    
    def rif_private_message_list(self, task=''):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
         
        ev = copy.deepcopy(rif_events.rif_private_message_list)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token
        
        # send event
        request = f"@JSON;{json.dumps(ev)}"
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        print(err)
        return err 

    
    def rif_news_list(self, task=''):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
         
        ev = copy.deepcopy(rif_events.rif_news_list)
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token
        
        # send event
        request = f"@JSON;{json.dumps(ev)}"
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        print(err)
        return err

    def dex_change_screen(self, new_screen_name, task=''):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
        
        ev = copy.deepcopy(rif_events.dex_change_screen)
        
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        ev['params']['new_screen_name'] = new_screen_name 

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        print(err)
        return err

        
    def dex_change_password(self, old_password, new_password, task=''):
        if not self.logged_in:
            print("You must first of all log in and create a new session.")
            return DopError(1, "Not logged in")
        
        ev = copy.deepcopy(rif_events.dex_change_password)
        
        # session info
        ev['session'] = self.session
        ev['task'] = task
        ev['params']['auth_token'] = self.auth_token

        ev['params']['old_password'] = old_password
        ev['params']['new_password'] = new_password 

        # send event
        request = f"@JSON;{json.dumps(ev)}"
        err = self._app_protocol.write_to_endpoint(request, self.endpoints['wbl_api'], self.auth_header)
        print(err)

        return err