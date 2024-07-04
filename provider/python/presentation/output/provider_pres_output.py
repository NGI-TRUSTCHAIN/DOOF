#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

from abc import ABC, abstractmethod
from common.python.error import DopError
from common.python.event import DopEvent
from provider.python.provider import Provider


class outputPresentationProvider(Provider):
    @abstractmethod
    def write(self, msg: str, additional_info: dict) -> DopError:
        pass

    @abstractmethod 
    def writeEvent(self, msg: DopEvent, additional_info: dict) -> DopError:
        pass

    @abstractmethod
    def write_to_endpoint(self, msg, endpoint, additional_info: dict) -> DopError:
        pass