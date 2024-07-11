#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

from datetime import datetime
from typing import Tuple, List


from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.model.models import Session
from common.python.model.schemas import SessionSchema
from common.python.new_processor_env import ProcessorEnvs
from common.python.utils import DopUtils

class UpdateSessionProcessor(ProcessorProvider):
   
    
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = "*"

    def init(self, config: str) -> DopError:
        self._config = config
        return DopError()

    def open(self) -> DopError:
        return DopError()

    def close(self) -> DopError:
        return DopError()


    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) -> DopError:
        """
        Processor assumes that event which was received belongs to an active session
        of a user (auth_macro) and updates the last_updated field of this session in the database. 
        """
        db = envs.db_provider
        payload = event.payload.to_dict()

        session = event.header.session
        token = payload.get('auth_token', None)
        
        session_obj, perr = db.get_session(where={'token': token,
                                            'value': event.header.session},
                                    )
        if perr.isError():
            perr.notifiable = False 
            return perr 
        if session_obj is None:
            err = DopError(1)
            err.notifiable = False
            return err
        
        update = {
            "last_updated":datetime.utcnow()
        } 
        session_update = Session(
            client=session_obj.client,
            value=session,
            last_updated=datetime.utcnow()
        )

        perr = db.update_session(session_obj.id, **SessionSchema().dump(session_update))
        if perr.isError():
            return perr 

        return DopError()
    
    