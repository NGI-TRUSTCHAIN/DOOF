
#   SPDX-License-Identifier: Apache-2.0
#   © Copyright Ecosteer 2024
#   ver:     1.0
#   auth:    georgiana
#   date:    13/05/2024

import sys
from typing import Tuple, Optional, Union


from abc import ABC, abstractmethod
from common.python.error import DopError
from common.python.event import DopEvent
from provider.python.provider import Provider


class blockchainWorkerProvider(Provider):
    
    # on_error
    # on_data
    # userdata
    # init 
    # open
    # close
    # stopEvent 
    # ... 

    """
    Provider for the blockchain
    """
    @abstractmethod
    def begin_transaction(self) -> DopError:
        """
        """

    @abstractmethod
    def rollback(self) -> DopError:
        """
        """

    @abstractmethod
    def commit(self) -> DopError:
        """
        """
