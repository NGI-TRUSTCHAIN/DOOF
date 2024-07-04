#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024


from abc import ABC, abstractmethod

from common.python.error import DopError
from provider.python.provider import Provider


class inputPresentationProvider(Provider):


    def __init__(self):
        super().__init__()

    @abstractmethod
    def read(self) -> DopError:
        """Reads a message"""
 

    #   init
    #   open
    #   close

