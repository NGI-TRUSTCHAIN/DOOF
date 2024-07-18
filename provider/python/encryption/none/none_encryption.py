#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

from typing import Tuple 

from provider.python.encryption.crypto_provider_abstract import CryptoProvider
from common.python.error import DopError

class NoneEncryption(CryptoProvider):
    """
    This class is an implementation of the CryptoProvider that can be used
    to return the identity of the DopEvent.
    The capabilities and supported encodings are empty.
    
    """
    def __init__(self):
        super().__init__()
        
        self._name = "none"
        self._blocksize = 0 # bits 

        
        self._modes = ""
        self._keylengths = 0
    

    def init(self, config: str) -> DopError:
        """
        parse the config file and set the variables used
        to configure and use the processor
        :param config: string
        """
        return DopError()
    
    def open(self) -> DopError:
        """
        Open the connection with a provider using the configs options
        """
        return DopError()

    def close(self) -> DopError:
        """
        Close the connection with the provider
        """
        return DopError()

    @property
    def blocksize(self):
        return self._blocksize

    
    def capabilities(self) -> list:
        """
        NOTE 
        Do not send the plaintext capabilities in the message 
        listing the supported cipher as the client may decide to use it.
        """
        return [{'name': self._name, 'mode': self._modes, 'keylength': self._keylengths}]

    
    def encrypt_bytes(self, mess: bytes, params: dict, iv: bytes, key: bytes) -> Tuple[DopError,bytes]:
        return (DopError(), mess)
    

    def decrypt_bytes(self, mess: bytes, params: dict, iv: bytes, key: bytes) -> Tuple[DopError,bytes]:
        return (DopError, mess)
