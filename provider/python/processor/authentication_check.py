#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

import datetime
from typing import Tuple, List


from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.utils import DopUtils
from common.python.model.models import User

class AuthenticationCheckProcessor(ProcessorProvider):
    """
    This processor populates the auth_macro of the pipeline: it verifies that
    session and auth_token of input event exist in database.
    With the external auth service in place, all the events apart start_session
    will need to be authenticated  
    """
    
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
        Processor checks that: 
        1) The token exists inside the database and it corresponds to the correct session
        2) session is not expired
        """
        db = envs.db_provider
        data_stack = envs.data

        header = event.header
        payload = event.payload.to_dict()

        session = header.session
        token = payload.get('auth_token', None)
        
        session_obj, perr = db.get_session(where={'token': token,
                                            'value': event.header.session},
                                    )
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_SESSION_TOKEN)
            err.perr = perr
            err.notifiable = False
            
            return err
       
        if session_obj is None:
            err = DopError(DopUtils.ERR_PL_SESSION_TOKEN)
            err.notifiable = False
            return err
        
        # Check that the session is not expired
        if self._is_session_expired(session_obj):
            err = DopUtils.create_dop_error(DopUtils.ERR_SESSION_EXPIRED)
            err.notifiable = False
            
            return err

        # user
        user, perr = db.get_user(where = {'id': session_obj.client})
        if perr.isError() or user is None:
            # Infrastructural error
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            if perr.isError():
                err.perr = perr 
            return err 
        
        
        data_stack.push(User.__name__, user)
        return DopError()
    
    
    def _is_session_expired(self, session) -> bool:
        # TODO MAX_AGE can be a configuration value of this processor
        now = datetime.datetime.utcnow()
        difference = (now - session.last_updated).total_seconds()
        if difference > DopUtils.MAX_AGE:
            # expired
            return True
        return False
