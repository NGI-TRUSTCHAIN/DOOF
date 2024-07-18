#   SPDX-License-Identifier: Apache-2.0

#   © Copyright Ecosteer 2024

import sys
from typing import Tuple


from abc import ABC, abstractmethod
from common.python.error import DopError
from common.python.event import DopEvent
from provider.python.provider import Provider


class blockchainMonitorProvider(Provider):

    @abstractmethod
    #   extract block from DLT
    def getBlock(self, blockNumber: str) -> Tuple[DopError, dict]:
        pass

    @abstractmethod
    #   extract transaction receipt from DLT
    def getTransactionReceipt(self, transactionHash: str) -> Tuple[DopError, dict]:
        pass

    @abstractmethod
    #   calculate hash (whenever possible, by applying the hash functions
    #   exposed by the underlying blockchain network)
    def getHash(self, hashFun: str, input: str) -> Tuple[DopError,str]:
        pass
