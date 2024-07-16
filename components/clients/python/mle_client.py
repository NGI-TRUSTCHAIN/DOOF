# © Copyright Ecosteer 2024


import base64
import json
import random
from typing import Tuple
import secrets 

import sys
from telnetlib import DO

from pyrsistent import b
from common.python.utils import DopUtils 
from common.python.error import DopError
from common.python.mle_protocol import MLE_Protocol 

from provider.python.encryption.crypto_provider_abstract import CryptoProvider
 

class MLE_Client(MLE_Protocol): 
    def __init__(self, prov_available = False):
        super().__init__()
        self._key = None # bytes 
        self._b64_key = None 
        #self._chosen_ciphersuite = None
        self._prov_available = prov_available
        self._encryption_providers_info = None 




    @property
    def encryption_providers_info(self):
        return self._encryption_providers_info 

    @encryption_providers_info.setter 
    def encryption_providers_info(self, table):
        self._encryption_providers_info = table


    @property 
    def key(self):
        return self._key 
    
    @key.setter 
    def key(self, key: bytes):
        self._key = key 

    @property 
    def b64_key(self):
        """Needed by the BLL to get knowledge about the key 
        and transmit it to the back-end"""
        return self._b64_key 
    
    @b64_key.setter 
    def b64_key(self, key: bytes):
        self._b64_key = key 

    
    def choose_ciphersuite(self, backend_ciphersuites):
        """
        The backend_ciphersuites is known by the BLL and passed to this method.
        """ 
        str_back_ciphers = []
        for suite in backend_ciphersuites:
            str_suite = json.dumps(suite)
            str_back_ciphers.append(str_suite)
        
        own_ciphersuites = []
        for entry in self.encryption_providers_info:
            err, provider = self._load_crypto_provider(entry)
            provider_suites = provider.capabilities()
            for suite in provider_suites:
                own_ciphersuites.append(json.dumps(suite))

        
        both = list(set(str_back_ciphers) & set(own_ciphersuites))

        index = random.randint(0, len(both)-1)
        return json.loads(both[index])


    def generate_key(self, size: int):
        """ NOTE be careful with this command because it overwrites
        the current version of the key!!! """
        key_bytes = secrets.token_bytes(size)

        self._key = key_bytes   
        
        key_b64 = base64.standard_b64encode(key_bytes) 
        self._b64_key = key_b64.decode()



    def handle_mle_event(self, message: dict) -> Tuple[DopError, str]:
        """ INPUT
            {"session": "13ce80e2-012b-44b7-959c-db9ed0819ab2", 
            "cipher_suite_name": "plaintext",
            "integrity_fun":"crc16",
            "digest":"ad79",
            "payload" : # NO: "params"
                "cipher_params": {"cipher_suite_mode": "none",
                "cipher_suite_keylength": 0},
                "iv": iv_b64,
                "encoding" : "base64",
                "ciphertext" : ciphertext
                }
            }

            Return the decrypted ciphertext as a JSON message 
        """
        #pdb.set_trace()
        cipher_name = message['cipher_suite_name']
        integrity_fun = message['integrity_fun']
        digest = message['digest']

        err, cryptoProvider = self._load_crypto_provider(cipher_name)
        if err.isError():
            return err, b''

        # TODO error management
        err, unwrapped_string = self.unwrap_and_decrypt(cryptoProvider, message['params'], self._key)
        #print(unwrapped_string)
        if err.isError():
            return err, unwrapped_string

        if integrity_fun != '': 
            integrity_res = self.integrity_provider.integrity_check(unwrapped_string, digest, integrity_fun)

            print(f"Integrity check = {integrity_res}")
            if not integrity_res: 
                return (DopError(21268, "MLE Error: the recovered checksum does not match the one received."),
                        unwrapped_string)

        return (DopError(), unwrapped_string)


    def _load_crypto_provider(self, cipher_name) -> Tuple[DopError, CryptoProvider]:
        """To be called when performing encryption/decryption. 
        Only the name of the cipher is necessary, 
        as the rest of the information is available from the 
        configuration file."""
        provider_config = self.encryption_providers_info[cipher_name]

        tupleLoadProvider = DopUtils.load_provider(provider_config, self._prov_available)
        if tupleLoadProvider[0].isError():
            return (tupleLoadProvider[0], None) 
        
        print(f"21266; Encryption provider for {cipher_name} successfully loaded")
        provider = tupleLoadProvider[1]
        
        cp_confstring: str = provider_config['configuration']
        err: DopError = provider.init(cp_confstring)
        if err.isError(): 
            return (err, None)

        print(f"21266; Encryption provider for {cipher_name} successfully initialized")

        return (DopError(), provider)