#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

try: 
    import numpy as np
    from typing import Callable, Tuple
    from common.python.error import DopError
    from provider.python.provider import Provider
except ImportError:

    from common.error import DopError
    from provider.provider import Provider
    from provider.provider import Callable, Tuple


class IntegrityFunctionProvider(Provider):
    
    def __init__(self):
       
        self._integrity_functions = {
            'crc16': self.crc16
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

    @property 
    def integrity_functions(self):
        return self._integrity_functions

    def available_integrity_fun(self):
        return self._integrity_functions.keys()

    def select_integrity_function(self, key: str) -> Callable:
        try: 
            return self._integrity_functions[key]
        except: 
            return None

    # Call an encode() message on the string to be checked when passing it to this method
    def crc16(self, data: bytes) -> str:
        '''
        CRC-16-ModBus Algorithm
        Used to obtain the checksum
        '''
        data = bytearray(data)
        poly = 0xA001
        crc = 0x0000
        #crc = 0xFFFF
        for b in data:
            crc ^= (0xFF & b)
            for _ in range(0, 8):
                if (crc & 0x0001):
                    crc = ((crc >> 1) & 0xFFFF) ^ poly
                else:
                    crc = ((crc >> 1) & 0xFFFF)
        
        # reverse byte order if you need to
        # crc = (crc << 8) | ((crc >> 8) & 0xFF)

        #ret: str = hex(np.uint16(crc))[2:]
        #if np.mod(len(ret),2) > 0:
        #    ret = '0' + ret
        
        ret: str = "{:04x}".format(crc)

        #return np.uint16(crc)
        return ret

    def integrity_check(self, decrypted_mess: str, digest: str, integrity_fun: str) -> bool:
        """ Return true if the decrypted message has the same checksum as the integrity 
        check received; the integrity_check string is the checksum received. 
        Integrity_fun is a string description of the function used to digest the original plaintext 
        (e.g. crc16, SHA-256, ...) """
        res = False 
        if integrity_fun in self.integrity_functions:
            function = self.integrity_functions[integrity_fun]
            digest_decrypted = function(decrypted_mess.encode()) #encoded to UTF-8 bytes
            
            if digest_decrypted == digest:
                res = True 
        return res
