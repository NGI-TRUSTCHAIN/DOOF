#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

from typing import Tuple, List
from abc import abstractmethod, ABC

from provider.python.provider import Provider
from common.python.error import DopError
from common.python.event import DopEvent 
from common.python.new_processor_env import ProcessorEnvs

class ProcessorProvider(Provider):
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = None

    # on_error
    # on_data
    # userdata
    # init 
    # open
    # close
    # stopEvent 
    # ... 
    @abstractmethod
    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) \
            -> DopError:
        
        """
        Handle the event and run the processor logic

        :params event
        :params envs

        Return DopError: an indication of success or failure
        """