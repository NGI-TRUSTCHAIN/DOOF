#   SPDX-License-Identifier: Apache-2.0
#   © Copyright Ecosteer 2024
#   ver:     1.0
#   auth:    graz
#   date:    26/06/2024

from typing import Tuple, Optional, Union

from common.python.error import DopError
from common.python.utils import DopUtils
from provider.python.intermediation.worker.provider_worker import blockchainWorkerProvider


from web3 import Web3
from web3.datastructures import AttributeDict
from web3.exceptions import InvalidAddress
from web3.middleware import geth_poa_middleware

import time
import sys


#   errors
ERR_CANT_CALL   = 100
ERR_CALL_EXC    = 101
ERR_TRANS_EXC   = 102


class workerDoof(blockchainWorkerProvider):
    """
    Ethereum/Hyperledger provider
    """
    ETHER_STARTING_VALUE = 999

    def begin_transaction(self) -> DopError:
        return DopError()
    
    def rollback(self) -> DopError:
        return DopError()
    
    def commit(self) -> DopError:
        return DopError()
    



    def __init__(self):
        self.config = None
        self.contract_abi = None        #   the abi of the marketplace smart contract
        self.contract_address = None    #   the address of the marketplace smart contract
        self.owner_address = None       #   the marketplace owner (root)
        self.owner_password = None      #   the marketplace owner password
        self.w3 = None
        self.contract = None            #   marketplace contract address
        self.gas = 8000000              #   default gas

        super().__init__()



    def init(self, config) -> DopError:
        tupleConfig = DopUtils.config_to_dict(config)
        if tupleConfig[0].isError():
            self._on_error(tupleConfig[0]) 
            return tupleConfig[0]

        self.config = tupleConfig[1]
        return DopError()
    
    def getAbi(self, filepath: str) -> DopError:
        #   load the ABI and assign it to self.contract_abi
        try:
            with open(filepath) as f:
                self.contract_abi = f.read()
            #print('ABI:[' + self.contract_abi + ']')
        except:
            return DopError(1,"cannot read contract_abi file")
        
        return DopError(0,"")



    def open(self) -> DopError:

        provider = self.config.get('provider')
        endpoint = self.config.get('endpoint')
        #   get the contract address (this is the address of a DOOF smart contract)
        self.contract_address = self.config.get('contract_address')
        if not self.contract_address:
            print('missing contract address')
            return DopError(10)

        contract_abi_path = self.config.get('contract_abi')
        if not contract_abi_path:
            return DopError(101,"Doof provider configuration error; missing contract_abi path.")
        
        #   load the ABI file -> assign self_contract_abi
        err: DopError = self.getAbi(contract_abi_path)
        if err.isError():
            return err
        

        g = self.config.get('gas')
        if g != None:
            self.gas = int(g)

        self.owner_address = self.config.get('owner_address')
        if not Web3.isChecksumAddress(self.owner_address):
            self.owner_address = Web3.toChecksumAddress(self.owner_address)
        self.owner_password = self.config.get('owner_password')
        if not provider or \
                not endpoint or \
                not self.owner_address or \
                not self.owner_password:
            return DopError(102,"Ethereum provider configuration error; missing parameter.")
        try:
            web3_provider = self._get_provider(provider)
        except NameError as e:
            return DopError(103, "Blockchain communication provider is not known/undefined.")
        self.w3 = Web3(web3_provider(endpoint))
        self.w3.middleware_stack.inject(geth_poa_middleware, layer=0)
        is_connected = self.w3.isConnected()
        if not is_connected:
            return DopError(104, "Blockchain connection error.")
    
        #   everything good
        #   load the contract, the same contract instance will be
        #   used for any call
        err = self._get_doof()
        if err.isError():
            print('cannot load the DOOF smart contract')


        #   check if everything is allright
        #   run the test by calling the smart contract method
        err, members = self.members()
        return err

    def close(self) -> DopError:
        return DopError()

    def begin_transaction(self) -> DopError:
        return DopError()

    def rollback(self) -> DopError:
        return DopError()
        
    def commit(self) -> DopError:
        return DopError()
    
    def canCall(self) -> bool:
        return self.contract != None

    #=======================================================================================
    #   smart contract interfaces (provider APIs)
    #=======================================================================================

    #=======================================================================================
    #   utils
    #=======================================================================================

    def marketplaceAddress(self, app_address) -> Tuple[DopError, str]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),'')
        b_address: bytes
        try:
            b_address = self.contract.functions.marketplaceAddress(app_address).call()
        except Exception as e:
            return DopError((ERR_CALL_EXC),'')

        address = '0x' + b_address.hex()
        return (DopError(),address)
        
    def marketplaceHash(self, data) -> Tuple[DopError, str]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),'')
        b_hash: bytes
        try:
            b_hash = self.contract.functions.marketplaceHash(data).call()
        except Exception as e:
            return DopError((ERR_CALL_EXC),'')

        hash = '0x' + b_hash.hex()
        return (DopError(),hash)

    #=======================================================================================
    #   membership
    #=======================================================================================
    def members(self) -> Tuple[DopError, list]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),[])
        
        b_members: list
        try:
            b_members = self.contract.functions.members().call({'from': self.owner_address, 'gas': self.gas})
        except Exception as e:
            return DopError((ERR_CALL_EXC),[])
        
        members = []
        for m in b_members:
            members.append('0x' + m.hex())
        
        return (DopError(),members)
    

    def memberAddress(self, index: int) -> Tuple[DopError, str]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),'')
        
        res: list
        try:
            res = self.contract.functions.memberAddress(index).call()
        except Exception as e:
            return DopError((ERR_CALL_EXC),'')

        err = DopError(res[0])
        if err.isError():
            return (err,'')

        address = '0x' + res[1].hex()
        return (err,address)
    
    
    def memberCreate(self
        ,   a_address:      str     #   application layer address
        ,   a_secret:       str     #   primary secret
        ,   a_proxy_secret: str     #   proxy secret
        ) -> Tuple[DopError, str]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),'')
        
        try:
            transaction = self._generate_transaction(_from=self.owner_address,
                                                     password=self.owner_password,
                                                     unlock=True)
            tx_hash = self.contract.functions.memberCreate(a_address, a_secret, a_proxy_secret).transact(transaction)
            tx_hash = tx_hash.hex()
        except Exception:
            return (DopError(ERR_TRANS_EXC),'')
        return (DopError(),tx_hash)


    def memberInfo(self
        ,   mkt_member_addr: str                #   mkt address of the member to be retrieved
        ,   mkt_supplicant_addr: str            #   mkt address of the supplicant
        ,   supplicant_proxy_secret: str        #   proxy secret of the supplicant
    ) -> Tuple [DopError, object]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),{})
        
        info: list
        try:
            info = self.contract.functions.memberInfo(mkt_member_addr, mkt_supplicant_addr, supplicant_proxy_secret).call()
        except Exception as e:
            return DopError((ERR_CALL_EXC),{})
        
        err = DopError(info.pop(0))
        if err.isError():
            return (err,{})
        
        ret = {}
        ret['balance']=info[0]
        return (DopError(),ret)


    #=======================================================================================
    #   products
    #=======================================================================================


    def products(self) -> Tuple[DopError, list]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),[])
        
        b_products: list
        try:
            b_products = self.contract.functions.products().call({'from': self.owner_address, 'gas': self.gas})
        except Exception as e:
            return DopError((ERR_CALL_EXC),[])
        
        products = []
        for m in b_products:
            products.append('0x' + m.hex())

        return (DopError(),products)



    def productAddress(self, index: int) -> Tuple[DopError, str]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),'')
        
        res: list
        try:
            res = self.contract.functions.productAddress(index).call()
        except Exception as e:
            return DopError((ERR_CALL_EXC),'')

        err = DopError(res[0])
        if err.isError():
            return (err,'')

        address = '0x' + res[1].hex()
        return (err,address)


    def productGet(self
        ,   mkt_product_addr: str               #   mkt address of the product
        ,   slot_selector: int                  #   select the slot to get SLOT_GLOBAL(0), SLOT_VAULT(1), SLOT_PROXY(2), SLOT_URL(3)
        ,   mkt_supplicant_addr: str            #   mkt address of the supplicant
        ,   supplicant_proxy_secret: str        #   proxy secret of the supplicant
    ) -> Tuple [DopError, str]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),'')
        
        data: str
        try:
            data = self.contract.functions.productGet(
                mkt_product_addr
            ,   slot_selector
            ,   mkt_supplicant_addr
            ,   supplicant_proxy_secret).call()
        except Exception as e:
            return DopError((ERR_CALL_EXC),'')
        
        err = DopError(data[0])
        if err.isError():
            return (err,'')
        return (DopError(),data[1])
    
    def productInfo(self
        ,   mkt_product_addr: str               #   mkt address of the product
        ,   mkt_supplicant_addr: str            #   mkt address of the supplicant
        ,   supplicant_proxy_secret: str        #   proxy secret of the supplicant
    ) -> Tuple [DopError, object]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),{})
        
        data: str
        try:
            data = self.contract.functions.productInfo(mkt_product_addr, mkt_supplicant_addr, supplicant_proxy_secret).call()
        except Exception as e:
            return DopError((ERR_CALL_EXC),{})
        
        err = DopError(data.pop(0))
        if err.isError():
            return (err,{})
        #   data holds the following values:
        #   0   owner addr
        #   1   payee
        #   2   balance
        #   3   price
        #   4   period
        ret = {}
        ret['owner']    ='0x' + data[0].hex()
        ret['payee']    ='0x' + data[1].hex()
        ret['balance']  =data[2]
        ret['price']    =data[3]
        ret['period']   =data[4]

        return (DopError(),ret)


    def productUpdate(self
        ,   mkt_product_addr: str       #   intermediation layer product address
        ,   slot_selector: int          #   select the slot to get SLOT_GLOBAL(0), SLOT_VAULT(1), SLOT_PROXY(2), SLOT_URL(3)
        ,   owner_proxy_secret: str     #   product's owner proxy secret
        ,   new_data: str               #   data to be propagated to the slot
        ) -> Tuple[DopError, str]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),'')
        
        try:
            transaction = self._generate_transaction(_from=self.owner_address,
                                                     password=self.owner_password,
                                                     unlock=True)
            tx_hash = self.contract.functions.productUpdate(
                mkt_product_addr
            ,   slot_selector
            ,   owner_proxy_secret
            ,   new_data).transact(transaction)
            tx_hash = tx_hash.hex()
        except Exception:
            return (DopError(ERR_TRANS_EXC),'')
        return (DopError(),tx_hash)



    def productCreate(self
        ,   a_address:      str     #   application layer address (for the new product)
        ,   mkt_owner_addr: str     #   intermediation layer address of the product's owner
        ,   mkt_payee_addr: str     #   intermediation layer address of the product's payee
        ,   a_proxy_secret: str     #   proxy secret of the product's owner
        ,   price: int
        ,   period: int
        ) -> Tuple[DopError, str]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),'')
        
        try:
            transaction = self._generate_transaction(_from=self.owner_address,
                                                     password=self.owner_password,
                                                     unlock=True)
            tx_hash = self.contract.functions.productCreate(
                a_address
            ,   mkt_owner_addr
            ,   mkt_payee_addr
            ,   a_proxy_secret
            ,   price
            ,   period).transact(transaction)
            tx_hash = tx_hash.hex()
        except Exception:
            return (DopError(ERR_TRANS_EXC),'')
        return (DopError(),tx_hash)


    def productSubscriptions(self
        ,   mkt_product_addr:           str         #   intermediation layer product address
        ,   mkt_supplicant_addr:        str         #   intermediation layer supplicant address
        ,   supplicant_proxy_secret:    str         #   supplicant proxy secret
        ) -> Tuple[DopError, list]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),[])
        
        b_subscriptions: list
        try:
            b_subscriptions = self.contract.functions.productSubscriptions(
                mkt_product_addr
            ,   mkt_supplicant_addr
            ,   supplicant_proxy_secret
            ).call()
        except Exception as e:
            return DopError((ERR_CALL_EXC),[])
        
        err = DopError(b_subscriptions[0])
        if err.isError():
            return (err, [])
        subscriptions = []
        for m in b_subscriptions[1]:
            subscriptions.append('0x' + m.hex())

        return (DopError(),subscriptions)



    #=======================================================================================
    #   subscriptions
    #=======================================================================================

    def subscriptionCreate(self
        ,   a_address:      str     #   application layer address (for the new subscription)
        ,   mkt_product_addr: str   #   intermediation layer address of the product (referenced by the subscription)
        ,   mkt_sub_addr: str       #   intermediation layer address of the subscriber
        ,   sub_proxy_secret: str   #   proxy secret of the subscriber
        ) -> Tuple[DopError, str]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),'')
        
        try:
            transaction = self._generate_transaction(_from=self.owner_address,
                                                     password=self.owner_password,
                                                     unlock=True)
            tx_hash = self.contract.functions.subscriptionCreate(
                a_address
            ,   mkt_product_addr
            ,   mkt_sub_addr
            ,   sub_proxy_secret
            ).transact(transaction)
            tx_hash = tx_hash.hex()
        except Exception:
            return (DopError(ERR_TRANS_EXC),'')
        return (DopError(),tx_hash)


    def subscriptionDelete(self
        ,   mkt_subscription_addr: str  #   application layer subscription address
        ,   mkt_product_addr: str       #   intermediation layer address of the product (referenced by the subscription)
        ,   mkt_sub_addr: str            #   intermediation layer address of the subscriber
        ,   sub_proxy_secret: str           #   proxy secret of the subscriber
        ) -> Tuple[DopError, str]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),'')
        
        try:
            transaction = self._generate_transaction(_from=self.owner_address,
                                                     password=self.owner_password,
                                                     unlock=True)
            tx_hash = self.contract.functions.subscriptionDelete(
                mkt_subscription_addr
            ,   mkt_product_addr
            ,   mkt_sub_addr
            ,   sub_proxy_secret
            ).transact(transaction)
            tx_hash = tx_hash.hex()
        except Exception:
            return (DopError(ERR_TRANS_EXC),'')
        return (DopError(),tx_hash)




    def subscriptionInfo(self
        ,   mkt_subscription_addr: str          #   mkt address of the subscription
        ,   mkt_supplicant_addr: str            #   mkt address of the supplicant
        ,   supplicant_proxy_secret: str        #   proxy secret of the supplicant
    ) -> Tuple [DopError, object]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),{})
        
        data: str
        try:
            data = self.contract.functions.subscriptionInfo(mkt_subscription_addr, mkt_supplicant_addr, supplicant_proxy_secret).call()
        except Exception as e:
            return DopError((ERR_CALL_EXC),{})
        
        err = DopError(data.pop(0))
        if err.isError():
            return (err,{})
        #   data holds the following values:
        #   0   product addr
        #   1   subscriber addr
        #   2   tog
        #   3   status
        ret = {}
        ret['product']    ='0x' + data[0].hex()
        ret['subscriber']    ='0x' + data[1].hex()
        ret['tog']  =data[2]
        ret['status']    =data[3]

        return (DopError(),ret)


    def subscriptionStatusGet(self
        ,   mkt_subscription_addr: str          #   mkt address of the subscription
        ,   mkt_supplicant_addr: str            #   mkt address of the supplicant
        ,   supplicant_proxy_secret: str        #   proxy secret of the supplicant
    ) -> Tuple [DopError, object]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),{})
        
        data: str
        try:
            data = self.contract.functions.subscriptionStatusGet(mkt_subscription_addr, mkt_supplicant_addr, supplicant_proxy_secret).call()
        except Exception as e:
            return DopError((ERR_CALL_EXC),{})
        
        err = DopError(data.pop(0))
        if err.isError():
            return (err,{})
        #   data holds the following values:
        #   0   status
        #   1   tog
        ret = {}
        ret['status']   =data[0]
        ret['tog']      =data[1]

        return (DopError(),ret)



    def subscriptionGrant(self
        ,   mkt_subscription_addr: str       #   intermediation layer product address
        ,   owner_proxy_secret: str     #   product's owner proxy secret
        ) -> Tuple[DopError, str]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),'')
        
        try:
            transaction = self._generate_transaction(_from=self.owner_address,
                                                     password=self.owner_password,
                                                     unlock=True)
            tx_hash = self.contract.functions.subscriptionGrant(
                mkt_subscription_addr
            ,   owner_proxy_secret
            ).transact(transaction)
            tx_hash = tx_hash.hex()
        except Exception:
            return (DopError(ERR_TRANS_EXC),'')
        return (DopError(),tx_hash)


    def subscriptionRevoke(self
        ,   mkt_subscription_addr: str       #   intermediation layer product address
        ,   owner_proxy_secret: str     #   product's owner proxy secret
        ) -> Tuple[DopError, str]:
        if not self.canCall():
            return (DopError(ERR_CANT_CALL),'')
        
        try:
            transaction = self._generate_transaction(_from=self.owner_address,
                                                     password=self.owner_password,
                                                     unlock=True)
            tx_hash = self.contract.functions.subscriptionRevoke(
                mkt_subscription_addr
            ,   owner_proxy_secret
            ).transact(transaction)
            tx_hash = tx_hash.hex()
        except Exception:
            return (DopError(ERR_TRANS_EXC),'')
        return (DopError(),tx_hash)







    ### PRIVATE METHODS ###

    
    @staticmethod
    def _get_provider(provider):
        if provider == 'ipc':
            return Web3.IPCProvider
        elif provider == 'http' or provider == 'https':
            return Web3.HTTPProvider
        elif provider == 'ws':
            return Web3.WebsocketProvider
        else:
            raise NameError
    


    def _get_doof(self) -> DopError:
        #   load the doof smart contract
        try:
            self.contract_address = self.w3.toChecksumAddress(self.contract_address)
            self.contract = self.w3.eth.contract(address=self.contract_address,abi=self.contract_abi)
        except Exception as e:
            return DopError(1)
        
        return DopError()
        


    
    def _unlock(self, 
            address, 
            password,
            time = 5):
        """
        Unlock an account with address and password for time secs
        """
        try:
            if not self.w3.isChecksumAddress(address):
                address = self.w3.toChecksumAddress(address)
            if self.w3.isAddress(address):
                check = self.w3.personal.unlockAccount(address,
                                                       password,
                                                       time)
            else:
                raise InvalidAddress('Invalid address when trying to unlock '
                                     'account')
        except Exception:
            raise
        return check



    def _lock(self, account):
        self.w3.personal.lockAccount(account)

    
    def _generate_transaction(self,
            unlock=False,
            password=None,
            **kwargs):
        _from = kwargs.pop('_from', None)
        if not _from:
            raise AttributeError(
                'In order to make a transaction you need a _from attribute '
                '(with underscore)'
            )
        kwargs['from'] = self.w3.toChecksumAddress(_from)
        if 'value' in kwargs:
            kwargs['value'] = int(kwargs['value'])
            # self.w3.toWei(float(kwargs['value']), 'ether')
        if unlock:
            self._unlock(kwargs['from'], password)
        if not kwargs.get('gas', None):
            kwargs['gas'] = self.w3.eth.getBlock('latest').gasLimit
        return kwargs

    

        