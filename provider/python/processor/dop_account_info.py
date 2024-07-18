#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

# author:       georgiana
# date:         03/07/2024
# version:      1.0


from typing import Tuple, List

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.utils import DopUtils

from common.python.model.models import User, AccountRole
from common.python.model.schemas import AccountRoleSchema



class DopAccountInfoProcessor(ProcessorProvider):

    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = "dop_account_info" 

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
        This events is typically emitted by a client who wants to retrieve his/her 
        account information, including username, screen name and balance on intermediation 
        platform

        event:
        {
            "session":"8abbc354-7258-11e9-a923-1681be663d3e",
            "task":"1",
            "event":"dop_account_info", 
            "params": {
                "auth_token":"hjkhjk456sl$$"
            }
        }

        """
        


        if event.header.event == self._event_type:
            return self._handle_dop_account_info(event, envs)
        elif self._event_type in envs.events.properties():
            to_process = envs.events.pop(self._event_type)

            for ev in to_process : 
                out = self._handle_dop_account_info(ev, envs)
                
                if out.isError():
                    return out 
                

        return DopError()
    
    def _handle_dop_account_info(self, event: DopEvent, envs: ProcessorEnvs) -> DopError:

        db = envs.db_provider
        blk = envs.blk_provider

        payload = event.payload.to_dict()
        
        header = event.header
        session = header.session
        task = header.task
        phase = 1

        
        # get authenticated user from stack 
        try:
            user = envs.data.get(User.__name__)[0]
        except:
            #perr =  DopError(999, "missing data from pipeline data stack")
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            #err.perr = perr 
            return err

     
        if user.blk_address is None:
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                    "err" : DopUtils.ERR_USER_ADDRESS['id'],
                    "phase": phase
            })))
            return DopError()

        #account_info, perr = blk.account_info(user.blk_address, user.blk_address, user.blk_password)
        
        
        # NOTE the blk info may be optional; if the account was not yet enabled
        # on blk but has a username, like the admin does, they may still want to see their info
        perr, account_info = blk.memberInfo(user.blk_address,user.blk_address,user.blk_password)
        
        
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_IP_ACCOUNT)
            err.perr = perr 
            return err 
        
        roles, perr = db.get_account_roles_str(where={'account_id': user.id})
        


        balance = account_info.get('balance', '-1')
        err = 1 if balance == -1 else 0
        event_payload = DopEventPayload({
            "err" : err,
            "phase":phase,
            "info": {
                "account_id": user.id,
                "balance": balance,
                "username": user.username,
                "screen": user.name,
                "roles": roles
            }
        })

        

        envs.events.push(header.event, DopEvent(header, event_payload))
        return DopError()