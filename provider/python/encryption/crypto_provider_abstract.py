# © Copyright Ecosteer 2024

#   version:    1.1
#   date:       12/06/2023
#   author:     georgiana-bud

# VERSION 1.1
# - added try - except block for usage of module in both python and micropython

try:
    from common.python.error import DopError
    from provider.python.provider import Provider

    from abc import ABC, abstractmethod 
    from typing import Tuple

except ImportError:
    #print("micropython")
    from common.error import DopError
    from provider.provider import Provider 
    from provider.provider import ABC, abstractmethod 
    from provider.provider import Tuple


class CryptoProvider(Provider):

    def __init__(self):
       super().__init__()
    
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


    def _zero_pad(self, blocksize:int, mess: str) -> str:
        """ Define a 0 padding scheme. Blocksize is in bits"""
        bytes_blocksize = int(blocksize/8) 
        
        pad: int = 0 if (len(mess) % bytes_blocksize) == 0 else bytes_blocksize - (len(mess) % bytes_blocksize)
        res = mess 
        while pad > 0: 
            res = res + chr(0)
            pad = pad - 1
        return res

    def _remove_zero_padding(self, blocksize: int, mess: str) -> str:
        """ Remove the padding added with zero_pad method. 
        Only remove padding from last block. Blocksize is in bits """
        bytes_blocksize = int(blocksize/8)

        last_block_start = len(mess) - bytes_blocksize
        mess_1 = mess[0: last_block_start] # left out the last block
        mess_2 = mess[last_block_start: ] # last block, take off padding from here
        i_pad = mess_2.find(chr(0))
        if i_pad > 0:
            mess_2 = mess_2[:i_pad] # take only chars up to the padding
        
        mess = mess_1 + mess_2
        return mess

    def _zero_pad_bytes(self, blocksize:int, mess: bytes) -> bytes:
        """ Define a 0 padding scheme for a bytes input. Blocksize is in bits"""

        output_b_array = bytearray(mess)

        bytes_blocksize = int(blocksize/8) 
        pad = 0 if (len(mess) % bytes_blocksize) == 0 else int(bytes_blocksize - (len(mess) % bytes_blocksize))
        
        padding = bytes(pad)
        output_b_array.extend(padding)
        return bytes(output_b_array)


    def _remove_zero_padding_bytes(self, blocksize: int, mess: bytes) -> bytes:
        """ Remove the padding added with zero_pad method. 
        Only remove padding from last block. Blocksize is in bits """
        bytes_blocksize = int(blocksize/8)

        last_block_start = len(mess) - bytes_blocksize
        output = bytearray(mess[0: last_block_start]) # left out the last block
        mess_2 = mess[last_block_start: ] # last block, take off padding from here
        
        # Search for the first index of the padding byte \x00 
        i = len(mess_2) 
        while i > 0 and chr(mess_2[i-1]) == '\x00':
            i -= 1


        output.extend(mess_2[0: i])

        return bytes(output)

    @property 
    @abstractmethod
    def blocksize(self):
        pass

    
    @abstractmethod
    def capabilities(self) -> list:
        """ 
        Return an array, a list of supported modes and key length
        TODO add also the supported encodings
        """

    
    @abstractmethod 
    def encrypt_bytes(self, mess: bytes, params: dict, iv: bytes, key: bytes) -> Tuple[DopError, bytes]:
        """ 
        Example params:
        {'mode':'CBC', 'keylength': '32'}    

        The params are a selector of the cryptographic capabilities of this cipher. 
    
        This method should be used by the workers to encrypt a binary message or
        generic length. 

        Mode, keylength and key are sent by the client; Initialization vector
        is set by the back-end, and then sent to the client (if it is used in the given mode,
        else it is empty string)

        Given the need to account for different encryption algorithms implementations, this method
        is very generic. It should:
        - initialize the specific cipher based on the params, the iv and the key
        - encrypt the message
        - return the padded, encrypted message in binary format
        """
  
      
    @abstractmethod
    def decrypt_bytes(self, mess: bytes, params: dict, iv: bytes, key: bytes) -> Tuple[DopError,bytes]:
        """ 
        Example params:
        {'mode':'CBC', 'keylength': '32'}

        This message should be used by the client to decrypt a binary message.

        Mode, keylength and key are set by the client; Initialization vector
        is set by the back-end, and then sent to the client (if it is used in the given mode,
        else it is empty string)

        Given the need to account for different encryption algorithms 
        implementations, this method is very generic. It should:
        - initialize the specific cipher based on the parameters
        - decrypt the message
        - return the unpadded, decrypted message in binary format
        """

    
