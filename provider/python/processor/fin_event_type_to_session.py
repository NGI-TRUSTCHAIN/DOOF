#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

import copy
from typing import Tuple
import json
import base64

from provider.python.processor.finally_processor_provider import FinallyProcessorProvider
from common.python.error import DopError
from common.python.event import DopEvent, TransportEventHeader, DopEventPayload

from common.python.pipeline_memory import PipelineMemory


class EventTypeToSessionProcessor(FinallyProcessorProvider):
    """
    This is a processor needed for the transformation of the events 
    placed in events cache by previous processors from the pipeline; 
    The processor assumes the pipeline events stack contains 
    "event_type" --> list of events
    It places each event in the list in another list indexed by its session

    """
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


    # on_error
    # on_data
    # userdata
    # init 
    # open
    # close
    # stopEvent 
    # ... 
    def handle_pipeline_stack(self, pipeline_stack: dict, providers: dict) \
            -> DopError:
        
        """
        Process the contents of pipeline_events: 
        for each property in pipeline_events:
            for each event in pipeline_events.pop(property) : 
                session = event.header.session
                push event in pipeline_event.session 
                                
        """
        for event_type in pipeline_stack['events'].properties():
            for event in pipeline_stack['events'].pop(event_type):

                session = event.header.session
                event_dict = event.to_dict()
                event_dict.pop('session')
                event.from_dict(event_dict)
                pipeline_stack['events'].push(session, event)
                                        

        return DopError()

