#   SPDX-License-Identifier: Apache-2.0

#   © Copyright Ecosteer 2024
#	auth:	graz
#	ver:	1.0
#	date:	06/06/2024


import time
from typing import Tuple


from web3 import Web3
from web3.middleware import geth_poa_middleware

from provider.python.intermediation.monitor.provider_monitor import blockchainMonitorProvider
from common.python.error import DopError
from common.python.event import DopEvent
from common.python.utils import DopUtils


class monitorEthereum(blockchainMonitorProvider):
    def __init__(self):
        self.i_configured: bool = False
        self.i_open: bool = False
        self.i_retries: int = 0
        self.i_max_retries: int = 5                              #   default max retries

        super().__init__()

    
    def init(self, connstring: str) -> DopError:      
        self.i_connstring: str = connstring
        self.p_url: bool = False
        self.p_usepoamiddleware: bool = False
        self.i_url: str
        self.i_usepoamiddleware: bool

        #   connstring example
        #   url=http://10.170.30.61:8501;poamiddleware=yes;
        tupleConfig = DopUtils.config_to_dict(connstring)
        if tupleConfig[0].isError():
            return tupleConfig[0]

        d_config: dict = tupleConfig[1]
        if 'url' in d_config:
            self.i_url = d_config['url']
            self.p_url = True
        
        if 'poamiddleware' in d_config:
            self.i_usepoamiddleware = (d_config['poamiddleware']=='yes')
            self.p_usepoamiddleware = True

        if 'rc' in d_config:
            self.i_max_retries = int(d_config['rc'])

        if (self.p_url and self.p_usepoamiddleware) != True:
            return DopError(1,"Invalid connstring")

        self.i_configured = True
        return DopError()

    def close(self) -> DopError:
        self.i_open = False
        return DopError()

    def __open(self) -> DopError:
        #   private member
        try:
            self.i_internal_provider = Web3.HTTPProvider(self.i_url, request_kwargs={'timeout': 10})
            self.i_provider = Web3(self.i_internal_provider)

            #   in case the consensus algorithm is of type POA
            if self.i_usepoamiddleware == True:
                self.i_provider.middleware_stack.inject(geth_poa_middleware, layer=0)

            #   test the connection etc. (this way, if the provider cannot be opened, 
            #   this method will catch an exception
            self.i_provider.eth.getBlock('latest')
            
            #   if no exception is raised, then the connection status will set to open
            return DopError()
        except:
            return DopError(1,"cannot open provider")

    def open(self) -> DopError:
        if self.i_configured == False:
            return DopError(1, "not configured")
        if self.i_open == True:
            self.close()

        #   loop with retries
        err: DopError = DopError()
        while self.i_retries <= self.i_max_retries:


            if self.stopEvent.is_exiting():
                #   an exit condition has been notified
                return DopError(10,"provider exiting")

            err = self.__open()
            if err.isError() == False:
                #   everything is fine
                self.i_retries = 0
                self.i_open = True
                return err
            else:
                if err.isRecoverable():
                    self.i_retries += 1
                else:
                    return err

            time.sleep(2)
        
        #   if we are here then the loop has iterated for more than self.i_max_retries
        err.rip()
        return err


    def __getBlock(self, option: str) -> Tuple[DopError, dict]:
            # see https://github.com/ethereum/web3.py/issues/782
            # <class 'web3.datastructures.AttributeDict'>
        try:
            if option == 'latest':
                block = self.i_provider.eth.getBlock(option)
                return (DopError(),dict(block))
            else:            
                blockNumber: int = int(option)
                block = self.i_provider.eth.getBlock(blockNumber)
                return (DopError(),dict(block))
        except:
            return (DopError(1,"exception getting block"),{})

            

    def getBlock(self, option: str) -> Tuple[DopError, dict]:
        self.i_retries = 0
        if self.i_open == False:
            err: DopError = self.open()
            if err.isError():
                return (DopError(1,"provider not open"),{})
        self.i_retries = 0

        while self.i_retries <= self.i_max_retries:

            if self.stopEvent.is_exiting():
                #   an exit condition has been notified
                #   such condition has to be considered an error, as the dict is empty
                return (DopError(10,"provider exiting"),{})

            tupleBlock = self.__getBlock(option)
            if tupleBlock[0].isError() == False:
                self.i_retries = 0
                return tupleBlock
            else:
                if tupleBlock[0].isRecoverable():
                    self.i_retries += 1
                    #       close and reopen the connection
                    self.close()
                    err = self.open()
                    if err.isError():       #   here an error is always not recoverable
                        return (err,{})
                else:
                    #       unrecoverable error
                    return (tupleBlock[0],{})
        
        #   end of loop
        err: DopError = DopError(1,"getblock unrecoverable error")
        err.rip()
        return (err,{})


    def __getTransactionReceipt(self, transactionHash: str) -> Tuple[DopError, dict]:
        try:
            transactionReceipt = self.i_provider.eth.getTransactionReceipt(transactionHash)
            if transactionReceipt == None:
                return (DopError(1,"transaction receipt not found"),{})
            return (DopError(),dict(transactionReceipt))
        except:
            return (DopError(2,"transaction receipt exception"),{})

    def getTransactionReceipt(self, transactionHash: str) -> Tuple[DopError, dict]:
        if self.i_open == False:
            return (DopError(1,"provider not open"),{})

        while self.i_retries <= self.i_max_retries:
            tupleTRec = self.__getTransactionReceipt(transactionHash)
            if tupleTRec[0].isError() == False:
                self.i_retries = 0
                return tupleTRec
            else:
                if tupleTRec[0].isRecoverable():
                    self.i_retries += 1
                    #       close and reopen the connection
                    self.close()
                    err = self.open()
                    if err.isError():       #   here an error is always not recoverable
                        return err
                else:
                    #       unrecoverable error from getTransactionReceipt
                    return tupleTRec[0]
        
        #   end of loop
        err: DopError = DopError(1,"gettransactionreceipt unrecoverable error")
        err.rip()
        return (err,{})

    def __getHash(self, hashFun: str, hashInput: str) -> Tuple[DopError, str]:
        
        #   this one has to be carefully designed
        #   hashFun is used to select the hash function type
        #   and it should be defined as an enum - or similar

        try:
            if hashFun == 'sha3':
                output: str = self.i_provider.sha3(text=hashInput).hex()
                #   see HexBytes class documentation
                #   please note that the hex is lower case
                return(DopError(),output)
            err: DopError = DopError(1,"hash type not supported")
            err.rip()
            return (err,"")
        except:
            return(DopError(2,"gethash exception"),"")

        

    def getHash(self, hashFun: str, hashInput: str) -> Tuple[DopError, str]:
     
        #   this one has to be carefully designed
        #   hashFun is used to select the hash function type
        #   and it should be defined as an enum - or similar
        if self.i_open == False:
            return (DopError(1,"provider not open"),"")

        while self.i_retries <= self.i_max_retries:
            tupleSha = self.__getHash(hashFun, hashInput)
            if tupleSha[0].isError() == False:
                self.i_retries = 0
                return tupleSha
            else:
                if tupleSha[0].isRecoverable():
                    self.i_retries += 1
                    self.close()
                    err = self.open()
                    if err.isError():
                        return (err,"")
                else:
                    return tupleSha

        #   end of loop
        err: DopError = DopError(1,"gethash unrecoverable error")
        err.rip()
        return (err,"")
