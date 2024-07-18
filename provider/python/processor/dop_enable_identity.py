#   SPDX-License-Identifier: Apache-2.0

#   version:    1.0
#   author:     georgiana
#   date:       01/07/2024 


from typing import Tuple, List
import json

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError, LogSeverity
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.model.models import User, Transaction
from common.python.model.schemas import UserSchema
from common.python.new_processor_env import ProcessorEnvs


from common.python.utils import DopUtils


class DopEnableIdentityProcessor(ProcessorProvider):
    

    def __init__(self): 
        super().__init__()
        self._config = ""
        self._airdrop = 999
        self._owner_address = ""
        self._owner_pwd = ""            # secret, no proxy_secret 
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
        phase = 0

        header = event.header
        payload = event.payload.to_dict()
        

        # get authenticated user from stack 
        try:
            user = envs.data.get(User.__name__)[0]
        except:
            #perr =  DopError(999, "missing data from pipeline data stack")
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            #err.perr = perr 
            return err

     

        if not user.is_admin:
            event_payload = DopEventPayload({
                    'err': DopUtils.ERR_OP_NOT_PERMITTED['id'],
                    #'msg': DopUtils.ERR_OP_NOT_PERMITTED['msg'],
                    "phase": phase
            })
            envs.events.push(header.event, DopEvent(header, event_payload))
            return DopError()

        # Data from payload

        subject = payload.get('subject')
        screen_name = payload.get('screen_name', subject)
        # generate a unique id for the user; overwrite it if user exists
        _id = str(DopUtils.create_uuid())

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
            _id = db_user.id
            update = True
            # admin provisioning itself or a user that was inserted manually in db


        blk_passw = DopUtils.make_random_password()  
        # NOTE address is computed here, but it will only be available when
        # the transaction will be completed 
        perr, address = blk.marketplaceAddress(_id)
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_IP_SIGNUP)
            err.perr = perr
            return err
        
        
        # TODO: extend account table to save 'secret' as well; blk_passw is used as proxy_secret 
        # ATTENTION: no two users can have the same 'subject' - so use a uuid instead 
        # as parameter to the blk provider call
        perr, tid = blk.memberCreate(_id, "secret", blk_passw) 

        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_IP_SIGNUP)
            err.perr = perr
            return err
        

        
        #logger.debug("New externally owned account created with address {}".format(address))
       
        # save transaction in db and  
        # return phase 0
        new_user =  User(
                id = _id,
                username = subject, 
                password = "", 
                blk_password=blk_passw,
                name=screen_name,
                blk_address=address
            )
        data = UserSchema().dump(new_user)
        data['original_session']  = event.header.session

        transaction = Transaction(
            hash=tid, 
            event_name=self._event_type,
            client=user.id,  
            task = header.task,
            params= json.dumps(data)
        )

        # save tid and data about user in blk_transaction table  
        perr = db.create_transaction(transaction)
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_TRANSACT_SAVE)
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

        