# © Copyright Ecosteer 2024

from abc import ABC
import base64
import secrets
from typing import Tuple


from common.python.error import DopError 
from provider.python.encoding.encoding_functions import EncodingFunctionProvider 
from provider.python.integrity.integrity_functions import IntegrityFunctionProvider 
from provider.python.encryption.crypto_provider_abstract import CryptoProvider

class MLE_Protocol(ABC): 
    def __init__(self):
        self._encoding_provider = None 
        self._integrity_provider = None 

        self._logger = None


    @property 
    def encoding_provider(self):
        return self._encoding_provider

    @encoding_provider.setter 
    def encoding_provider(self, encoding: EncodingFunctionProvider):
        self._encoding_provider = encoding

    
    @property 
    def integrity_provider(self):
        return self._integrity_provider

    @integrity_provider.setter 
    def integrity_provider(self, integrity: IntegrityFunctionProvider):
        self._integrity_provider = integrity


    @property 
    def logger(self):
        return self._logger
    
    @logger.setter
    def logger(self, logger):
        self._logger = logger 

    def encrypt_and_wrap(self, cipher: CryptoProvider, mess: str, params: dict, key: bytes, encoding: str) -> Tuple[DopError, dict]:
        """Pass the string version of the message to be encrypted, 
        together with the cipher and the configuration parameters. 
        Return the encrypted message inside a wrapper dictionary such as:
        OUT
        {
            "cipher_params": # the input params
                {"mode": params['mode'], 
                "keylength": params['keylength']},
            "iv": iv_b64, 
            "encoding" : self._encoding,
            "ciphertext" : ciphertext
        }

        This dictionary needs to be inserted into a DopEvent that 
        has a DopTransportHeader
        e.g. {
            "session" : "...",
            "cipher_suite_name" : "...",  # set by the caller of this function
            "integrity_fun":"...",
            "digest":"..."
            "params" : 
                THE OUTPUT OF THIS FUNCTION
            

        }
        """ 
        #   Initialization Vector is always encoded in base64
        iv = secrets.token_bytes(int(cipher.blocksize/8))
        iv_b64_bytes = base64.standard_b64encode(iv)
        iv_b64 = iv_b64_bytes.decode()  # UTF bytes -> str
        

        #  encrypt does not apply encoding, this 
        #  needs to be done only here
        
        # binary message 
        b_mess = mess.encode() # str -> bytes
        err, b_ciphertext = cipher.encrypt_bytes(b_mess, params, iv, key)

        if err.isError():
            #print(err.msg)
            return (err, {})
        
        # Encoding for interoperability and transmission
        err, encoder_function = self.encoding_provider.select_encoding(encoding) 
        if err.isError() or encoder_function is None:
            #print(err.msg)
            return (err, {})
        
        # encode binary -> text, cross-platform compatible format
        b_encoded_ciphertext = encoder_function(b_ciphertext)
        s_encoded_ciphertext = b_encoded_ciphertext.decode() # UTF bytes -> str


        return (DopError(),{"cipher_params": params,
            "iv": iv_b64, 
            "encoding" : encoding,
            "ciphertext" : s_encoded_ciphertext})


    def unwrap_and_decrypt(self, cipher: CryptoProvider, mess: dict, key: bytes) -> Tuple[DopError, str]:
        """Opposite of encrypt_and_wrap(). Takes as input the envelope with the 
        encrypted message and returns the decrypted string.
        Example of dictionary message passed to this function: 
        {
            "cipher_params":
                {"mode": "CBC" , 
                "keylength": "128"},
            "iv": iv_b64, 
            "encoding" : self._encoding,
            "ciphertext" : ciphertext # or plaintext in the case of the plaintext placeholder
        }
        
        """
        
        cipher_params = mess['cipher_params']
        encoding = mess['encoding']

        # IV
        iv_b64 = mess['iv']
        iv_b64_bytes = iv_b64.encode() # UTF str -> bytes
        iv_bytes = base64.standard_b64decode(iv_b64_bytes)
        
        # DECODE Ciphertext
        ciphertext_encoded:str = mess['ciphertext']
        ciphertext_bytes_encoded = ciphertext_encoded.encode() # UTF str -> bytes
        
        err, decoder_function = self._encoding_provider.select_decoding(encoding)
        if err.isError() or decoder_function is None:
            #print(err.msg)
            return (err, "")

        ciphertext_bytes = decoder_function(ciphertext_bytes_encoded)

        err, decrypted_bytes = cipher.decrypt_bytes(ciphertext_bytes, cipher_params, iv_bytes, key)

        if err.isError():
            #print(err.msg)
            return (err, "")

        decrypted_mess = decrypted_bytes.decode() # Bytes -> str

        
        return (DopError(), decrypted_mess) # either None or correct one