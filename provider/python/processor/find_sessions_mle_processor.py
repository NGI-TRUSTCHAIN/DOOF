#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

from typing import Tuple, List


from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.utils import DopUtils

class FindSessionsMLEProcessor(ProcessorProvider):

    
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = "*"
        self._multiple_sessions = True

    def init(self, config: str) -> DopError:
        self._config = config
        err, config_dict = DopUtils.config_to_dict(config)
        multiple = config_dict.get('multiple_sessions', "true") 
        if multiple.lower() == "false":
            self._multiple_sessions = False


        return DopError()

    def open(self) -> DopError:
        return DopError()

    def close(self) -> DopError:
        return DopError()


    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) -> DopError:
        db = envs.db_provider

        session = event.header.session

        if self._multiple_sessions:
            all_sessions_with_mle, perr = db.get_client_sessions_and_mle(session)
            if perr.isError():
                err = DopUtils.create_dop_error(DopUtils.ERR_SESSION_MLE_LOOKUP)
                err.perr = perr 

                # TODO is this notifiable?
                return err

        else: 
            all_sessions_with_mle, perr =  db.get_session_and_mle(session)
            # TODO the processor or the call to the provider method can perform a double
            # check on the validity of sessions (do not insert sessions which are already
            # expired and may have not been yet deleted) 
        
        
        if all_sessions_with_mle is None:
            err = DopError(DopUtils.ERR_PL_SESSION_TOKEN)
            err.notifiable = False
            return err

        envs.data.push_list_elements(session, all_sessions_with_mle)

        return DopError()