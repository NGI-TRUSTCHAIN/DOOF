#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

from datetime import datetime, timezone
from typing import Tuple, List

from provider.python.processor.provider_processor import ProcessorProvider

from common.python.error import DopError, LogSeverity
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.model.models import Session, EncryptedSession
from common.python.new_processor_env import ProcessorEnvs

from common.python.utils import DopUtils

class StartSessionProcessor(ProcessorProvider):

    def __init__(self):
        super().__init__()
        self._config = ""

    def init(self, config: str) -> DopError:
        self._config = config
        return DopError()

    def open(self) -> DopError:
        return DopError()

    def close(self) -> DopError:
        return DopError()

    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) \
            -> DopError:
            #-> List[Tuple[DopEvent, DopError]]:  NOTE: this was previous return value

        """
        This events is typically emitted by the DOOF Gateway when an authenticated client wants to start a 
        DOP session.

        event:
        {
            "session":"8abbc354-7258-11e9-a923-1681be663d3e",
            "task":"1",
            "event":"start_session",
            "params":   {
                            "subject":"example@example.com",
                            "auth_token":"hgjkdhjdkhj",
                            "session": "8abbc354-7258-11e9-a923-1681be663d3e"
                        }
        }

        """
        db = envs.db_provider

        payload = event.payload.to_dict()
        
        header = event.header
        session = header.session
        task = header.task

        event_header = DopEventHeader(session, task, header.event)

        username = payload.get('subject')
        token = payload.get('auth_token')

        user, perr = db.get_user_from_username(username)
        if perr.isError():
            # Infrastructural error
            err = DopError(DopUtils.ERR_PL_USER_NOT_FOUND['msg'], DopUtils.ERR_PL_USER_NOT_FOUND['id'])
            err.perr = perr
            return err
        
        if user is None:
            
            envs.events.push(event_header.event, DopEvent(event_header, DopEventPayload({
                "err" : DopUtils.ERR_PL_USER_NOT_FOUND['id'], 
                "msg": DopUtils.ERR_PL_USER_NOT_FOUND['msg']
            }))) 
            return DopError()

        
        session_obj = Session(
            client=user.id,
            value=session,
            token=token,
            last_updated=datetime.utcnow()
        )

        perr = db.create_session(session_obj)
        if perr.isError():
            # Infrastructural error
            err = DopError(DopUtils.ERR_PL_SESSION_NOT_CREATED['msg'], DopUtils.ERR_PL_SESSION_NOT_CREATED['id'])
            err.perr = perr
            return err 
 
        # Set up MLE to use None encryption

        # get the session id
        session_obj_w_id, err = db.get_session({'value':session, 'token':token})#, 'token':auth_token})
        session_id = session_obj_w_id.id


        # create the EncryptedSession object
        encrypted_session_obj = EncryptedSession(
            session_id = session_id,
            cipher_name = 'none',
            cipher_mode = 'none',
            cipher_keylength = -1, #in bits (then it is /8 to check length)
            key = 'none', # key is saved in the database in a textual format
            encoding = 'none',
            integrity_fun = 'none'
        )

        perr = db.create_encrypted_session(encrypted_session_obj)
        if perr.isError():
            # Infrastructural error
            err = DopError(DopUtils.ERR_PL_ENC_SESSION_NOT_CREATED['msg'],DopUtils.ERR_PL_ENC_SESSION_NOT_CREATED['id'])
            err.perr = perr
            err


        event_params = DopEventPayload({
                "err": 0,
                "msg": DopUtils.MSG_NEW_SESSION['msg'],
                "msg_id" : DopUtils.MSG_NEW_SESSION['id']
            })
        
        # push DopEvent onto stack and return DopError 
        envs.events.push(event_header.event,DopEvent(event_header, event_params))
        return  DopError()

        

