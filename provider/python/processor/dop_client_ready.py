#   SPDX-License-Identifier: Apache-2.0
#   © Copyright Ecosteer 2024

from typing import Tuple, List

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.utils import DopUtils


class DopClientReadyProcessor(ProcessorProvider):

    
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type =  "dop_client_ready"

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
        This event notifies the worker that the client is ready to receive 
        notifications on the session topic initiated by the start_session interaction. 
        Typically this event is emitted by a client which is already logged in.
        :param event:
        :param envs: A class with the properties used as arguments by all the processors
        event: 
        {
            "session":"8abbc354-7258-11e9-a923-1681be663d3e",
            "task":"1",
            "event":"client_ready",
            "params":   {
                    "auth_token":"890fghja%%432?98"
                        }
        }
        The processor assumes that session and auth_token are valid, as they are checked by
        the authentication macro, and replies to this imperative with a list of supported ciphers. 
        """
    
    
        if self._event_type == event.header.event:
            return self._handle_dop_client_ready(event, envs)
        return DopError()    
    
    def _handle_dop_client_ready(self, event, envs) -> DopError:
        
        blk = envs.blk_provider
        db = envs.db_provider
        crypto_tools = envs.crypto_providers
        phase = 1

        header = event.header
        params = event.payload.to_dict()
        
        session = header.session
        task = header.task
        response_header = DopEventHeader(session, task, "dop_cipher_suite")
	
        supported_ciphersuites = []
        for tool in crypto_tools:
            cipher = crypto_tools[tool]
            capabilities = []
            try: 
                capabilities = cipher.capabilities()
            except Exception as e:
                err = DopUtils.create_dop_error(DopUtils.ERR_CIPHER_SUITE)
                print(err)
            for c in capabilities:
                supported_ciphersuites.append(c)
            

        envs.events.push(header.event,DopEvent(header,DopEventPayload({
            "err": 0,
            "phase": phase,
            "cipher_suites": supported_ciphersuites
        })))
        return DopError()
