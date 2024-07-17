#   © Copyright Ecosteer 2024

import json
from typing import Tuple, List

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.utils import DopUtils, BlockchainEvents as be

from common.python.model.models import PurposeOfUsage


class DopPurposeListProcessor(ProcessorProvider):

    
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = "dop_purpose_list"

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
        This event returns a list ofpurpose of usages inserted
        by the user sending the event. 
        
        event:
        {
            "session":"8abbc354-7258-11e9-a923-1681be663d3e",
            "task":"1",
            "event":"dop_purpose_list",
            "params":   {
                            "auth_token": "890fghja%%432?98"
                        }
        }
        """

        if self._event_type == event.header.event:
                return self._handle_dop_purpose_list(event, envs)

        return DopError()    
    

    def _handle_dop_purpose_list(self, event, envs) -> DopError:
        db = envs.db_provider
        blk = envs.blk_provider
        payload = event.payload.to_dict() 
        header = event.header
        phase = 1
         
        #   check if user has authenticated
        user, perr = db.get_user_from_session({'value': header.session,
                                              'token': payload['auth_token']})
        if perr.isError():
            # Infrastructural error 
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            err.perr = perr
            return err
        
        if user is None: 
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                    "err" : DopUtils.ERR_PL_USER_NOT_FOUND['id'],
                    #"msg": DopUtils.ERR_PL_USER_NOT_FOUND['msg'],
                    "phase" : phase
            })))
            return DopError()
    

        purposes, perr = db.get_purpose_of_usage(where={'subscriber': user.id})
        
        if perr.isError(): 
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_PURPOSE_NOT_FOUND)
            err.perr = perr 
            return err 
        
        if isinstance(purposes, PurposeOfUsage):
            purposes = [purposes] 
        
        if purposes is None: 
            purposes = []

        envs.events.push(header.event, DopEvent(header, DopEventPayload({
            "err" : 0, 
            "phase" : phase,
            "set" : purposes
        })))

        return DopError()