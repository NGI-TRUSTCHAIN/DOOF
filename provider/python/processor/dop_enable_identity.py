#   SPDX-License-Identifier: Apache-2.0

#   © Copyright Ecosteer 2024
#   version:    1.0
#   author:     Georgiana
#   date:       24/01/2024

from typing import Tuple, List


from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError, LogSeverity
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.model.models import User, Transaction
from common.python.new_processor_env import ProcessorEnvs

from common.python.utils import DopUtils


class DopEnableIdentityProcessor(ProcessorProvider):
   

    def __init__(self): 
        super().__init__()
        self._config = ""
        self._airdrop = 999
        self._owner_address = ""
        self._owner_pwd = "ecosteer"        # secret, no proxy_secret 
        self._event_type = "dop_enable_identity"

    def init(self, config: str) -> DopError:
        if config:
            err, conf_dict = DopUtils.config_to_dict(config)
            if err.isError():
                return DopError(1,f"Error in configuring the {self._event_type} provider.")
            self._config = conf_dict

            config_airdrop = self._config.get('airdrop', None)
            owner= self._config.get('owner_address', None)
            owner_pwd = self._config.get('owner_password', None)
        
            if config_airdrop is not None:
                self._airdrop = int(config_airdrop)

            if owner is not None: 
                self._owner_address = owner

            if owner_pwd is not None:
                self._owner_pwd = owner_pwd
            


        return DopError()

    def open(self) -> DopError:
        return DopError()

    def close(self) -> DopError:
        return DopError()

    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) \
            -> DopError:
            
        """
        This events triggers the creation of an account on the intermediation platform. 
        Typically this event is emitted by a system administration as a provisioning step.
        The system administrator must be authenticated to auth_token must be valid.
        :param event:
        :param args: A class with the properties used as arguments by all the processors
        event: 
        {
            "session":"8abbc354-7258-11e9-a923-1681be663d3e",
            "task":"1",
            "event":"dop_enable_identity",
            "params":   {
                            "auth_token" : "888ghj=89l;#", 
                            "subject": "john.red@example.com",
                            "screen_name" : "name", 
                            "role" :"",
                            "recipient":""
                        }
        }
            Generate a blockchain password. 
            Create a blockchain user and return a new address
            Create new User
        """


        if self._event_type == event.header.event:
            return self._handle_dop_enable_identity(event, envs)
        return DopError()    
    

    def _handle_dop_enable_identity(self, event, envs) -> DopError:

        blk = envs.blk_provider
        db = envs.db_provider
        logger = envs.logger_provider 
        phase = 1 

        header = event.header
        payload = event.payload.to_dict()
        

        session = header.session
        task = header.task

        token = payload.get('auth_token')

        user, perr = db.get_user_from_session({
            'value': header.session,
            'token': token
        })
        if perr.isError():
            # Checks on auth_token: the session must belong to an enabled user (the admin in this case);
            # this check was done by auth macro; now there may have been a provider - infrastructural error    
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            err.perr = perr
            return err

        
        if user is None: 
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                    "err" : DopUtils.ERR_PL_USER_NOT_FOUND['id'],
                    #"msg": DopUtils.ERR_PL_USER_NOT_FOUND['msg'],
                    "phase": phase
            })))
            return DopError()
    

        if not user.is_admin:
            event_payload = DopEventPayload({
                    'err': DopUtils.ERR_OP_NOT_PERMITTED['id'],
                    #'msg': DopUtils.ERR_OP_NOT_PERMITTED['msg'],
                    "phase": phase
            })
            envs.events.push(header.event, DopEvent(header, event_payload))
            return DopError()


        subject = payload.get('subject')
        screen_name = payload.get('screen_name', subject)

        # check if new user exists already
        db_user, perr = db.get_user_from_username(subject)
        if db_user is not None and db_user.blk_address is not None:
            # user exists
            event_payload = DopEventPayload({
                    "err" : DopUtils.ERR_PL_USER_EXISTS['id'],
                    #"msg": DopUtils.ERR_PL_USER_EXISTS['msg'],
                    "phase": phase
            })
            envs.events.push(header.event, DopEvent(header, event_payload))
            return DopError()
        
        update = False
        if db_user is not None and db_user.blk_address is None :
                #and db_user.is_admin: 
            update = True
            # admin provisioning itself or a user that was inserted manually in db
        

        blk_passw = DopUtils.make_random_password()    
        address, blk_passw, perr = blk.create_user(subject, blk_passw)
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_IP_SIGNUP)
            err.perr = perr
            return err
        
        
        if update: 
            update_user = User(
                id = db_user.id,
                username = subject, 
                password = db_user.password, 
                blk_password=blk_passw,
                name=screen_name,
                blk_address=address
            )
            perr = db.update_user(update_user)
        else:
            
            # Create a db user
            new_user = User(
                username=subject,
                password="",
                blk_password=blk_passw,
                name=screen_name,
                blk_address=address
            )
            perr = db.create_user(new_user)
        
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_SIGNUP)
            err.perr = perr
            return err

        
        perr = blk.account_send(self._owner_address, address, self._owner_pwd, self._airdrop )
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_IP_SIGNUP)
            err.perr = perr
            return err 
        
        event_payload = DopEventPayload({
                "err": 0, 
                "phase": phase,
                "subject": subject, 
                "screen_name" : screen_name 
        })
        envs.events.push(header.event, DopEvent(header, event_payload))

        return DopError()

        