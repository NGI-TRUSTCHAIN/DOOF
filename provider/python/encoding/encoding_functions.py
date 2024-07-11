# © Copyright Ecosteer 2024

import base64
from typing import Callable, Tuple
from common.python.error import DopError
from provider.python.provider import Provider

class EncodingFunctionProvider(Provider): 
    
    def __init__(self):
        self._encoder = {
            'input' : self.input,
            'base64' : self.b64_encode
        }
        self._decoder = {
            'input' : self.input,
            'base64' : self.b64_decode
        }

    
    #attach_stop_event()
    #_on_error()
    #_on_data()
    #set_userdata()
    #set_on_data_callback
    #set_on_error_callback
    #stopEvent()
    #lastError()
    #set_lastError()
    #init() ABSTRACT
    #open() ABSTRACT
    #close() ABSTRACT
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


    def available_encodings(self):
        return self._encoder.keys()

    @property 
    def encoder(self):
        return self._encoder 
    
    @property
    def decoder(self):
        return self._decoder 

    def select_encoding(self, key: str) -> Tuple[DopError, Callable]:
        try: 
            return (DopError(),self._encoder[key])
        except: 
            return (DopError(1, f"Encoding '{key}' not supported. Returning the identity function."), 
            self._encoder[input])

    def select_decoding(self, key: str)-> Tuple[DopError, Callable]:
        try: 
            return (DopError(),self._decoder[key])
        except: 
            return (DopError(1, f"Encoding/decoding '{key}' not supported. \
            Returning the identity function"), self._encoder[input])

    def b64_encode(self, mess: bytes) -> bytes:
        """ Encode from a binary representation of bytes to another binary representation
        using base64 """ 
        return base64.standard_b64encode(mess)

    def b64_decode(self, mess: bytes) -> bytes:
        """ Decode from the binary representation to another binary representation
        using base64"""
        return base64.standard_b64decode(mess)

    def input(self, mess: bytes) -> bytes:
        return mess