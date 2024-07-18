#   SPDX-License-Identifier: Apache-2.0
#   © Copyright Ecosteer 2024

import json
from typing import Tuple, List
 
from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.utils import DopUtils, BlockchainEvents as be

from common.python.model.models import PurposeOfUsage


class DopPurposeCreateProcessor(ProcessorProvider):

    
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = "dop_purpose_create"

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
        This event creates a new purpose of usage. The emitter of the event 
        is the owner of this purpose.
        
        event:
        {
            "session":"8abbc354-7258-11e9-a923-1681be663d3e",
            "task":"1",
            "event":"dop_purpose_create",
            "params":   {
                            "auth_token": "890fghja%%432?98",
                            "label": "I want to use your data for this reason: XYZ",
                            "content": "url"
			}
        }
        """
    
        if self._event_type == event.header.event:
                return self._handle_dop_purpose_create(event, envs)

        return DopError()    
    

    def _handle_dop_purpose_create(self, event, envs) -> DopError:
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
        
        # insert purpose for this subscriber 
        label = payload.get("label", "")
        b64_label, err = DopUtils.to_base64(label)
        content = payload.get("content", "")
        content_b64, err = DopUtils.to_base64(content)

        purpose_id = str(DopUtils.create_uuid())
        
        purpose = PurposeOfUsage(
            id = purpose_id, 
            subscriber = user.id,
            label = b64_label, 
            url = content_b64
        )
        id, perr = db.create_purpose_of_usage(purpose)      

        if perr.isError():
            # infrastructural error
            # TODO eventualmente substitute this error message with something else 
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_SUB) 
            err.perr = perr
            return err 

        envs.events.push(header.event, DopEvent(header, DopEventPayload({
            "err" : 0,
            "phase" : phase,
            "label" : label, 
            "content" : content,
            "purpose_id" : id
        })))


        return DopError()