#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

from typing import Tuple, List
from abc import abstractmethod, ABC 


from provider.python.provider import Provider
from common.python.error import DopError
from common.python.event import DopEvent 
from common.python.new_processor_env import ProcessorEnvs

class FinallyProcessorProvider(Provider):
    def __init__(self):
        super().__init__()
        self._config = ""

    # on_error
    # on_data
    # userdata
    # init 
    # open
    # close
    # stopEvent 
    # ... 
    @abstractmethod
    def handle_pipeline_stack(self, pipeline_stack: dict, providers: dict) \
            -> DopError:
        
        """
        Handle the content pipeline stack events and data, by using the providers,
        and return a DopError indicating whether an error ocurred 
        """