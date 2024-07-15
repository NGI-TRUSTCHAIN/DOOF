# © Copyright 2024 Ecosteer

#   ver:    1.0
#   date:   30/05/2024
#   author: georgiana

import sys
from typing import Tuple, Type, Union


from abc import ABC, abstractmethod
from common.python.error import DopError
from common.python.event import DopEvent
from provider.python.provider import Provider

from common.python.model.models import User, Transaction, Product, Session, \
    EncryptedSession, Property, PropertyProduct

from common.python.model.models import ProductUsage
from common.python.model.models import PurposeOfUsage, ProductSubscription
from common.python.model.models import AccountRole


class providerPersistence(Provider):
    # on_error
    # on_data
    # userdata
    # init 
    # open
    # close
    # stopEvent 
    # ...

    
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

    

    @abstractmethod
    def create_user(self, user: User) -> DopError: 
        """
        """

    @abstractmethod
    def create_transaction(self, transaction: Transaction) -> DopError: 
        """
        """

    @abstractmethod
    def create_product(self, product: Product, uuid: str) -> Tuple[int, DopError]: 
        """
        """
    
    @abstractmethod
    def create_product_usage(self, product_usage: ProductUsage) -> DopError:
        """"""
    

    @abstractmethod
    def update_or_create_session(self, session: Session) -> DopError: 
        """
        """
        
    @abstractmethod 
    def create_session(self, session: Session) -> DopError:
        """
        """

    @abstractmethod
    def user_verify(self, username, password) -> DopError: 
        """
        """

    @abstractmethod
    def isOwner(self, publisher_id, product_address: str) \
           -> Tuple[bool, DopError]: 
        """
        """

    @abstractmethod
    def get_transaction(self, where: dict) \
            -> Tuple[Union[Transaction, list, None], DopError]: 
        """
        """ 

    @abstractmethod
    def get_user(self, where: dict = None) \
            -> Tuple[Union[User, list, None], DopError]: 
        """
        """

    @abstractmethod
    def get_product_reference(self, product_id) \
            -> Tuple[dict, DopError]: 
        """
        """


    @abstractmethod
    def get_client_sessions_and_mle(self, curr_client_session)\
            -> Tuple[list, DopError]:
        """"""

    @abstractmethod    
    def get_product(self, where: dict = None) \
            -> Tuple[Union[Product, list, None], DopError]: 
        """
        """

    
    @abstractmethod
    def get_sets_products(self, account_id, subset, where: dict = None) \
        -> Tuple[Union[dict, list, None], DopError]:
        """
        """
    
    
    @abstractmethod
    def get_other_products(self, account_id, where: dict= None) \
        -> Tuple[Union[dict, list, None], DopError]:
        """
        """


    @abstractmethod
    def get_product_by_blkaddress (self, blkaddress: str) \
            -> Tuple[dict, DopError]: 
        """
        """

    @abstractmethod
    def get_session(self, where: dict = None) \
            -> Tuple[Union[Session, list, None], DopError]: 
        """
        """

    @abstractmethod
    def get_user_from_session(self, where: dict) \
            -> Tuple[Union[User, None], DopError]: 
        """
        """

    @abstractmethod
    def get_subscription(self, user_id: int, product_id: str) \
            -> Tuple[dict, DopError]: 
        """
        """

    @abstractmethod
    def get_account_by_blkaddress(self, blkaddress: str) \
            -> Tuple[dict, DopError]: 
        """
        """

    @abstractmethod
    def get_account_by_session(self, session: str, auth_token: str) \
            -> Tuple[dict, DopError]: 
        """
        """

    @abstractmethod
    def get_transaction_by_hash(self, hash: str) \
            -> Tuple[dict, DopError]: 
        """
        """

    @abstractmethod
    def get_user_from_username(self, username: str) \
            -> Tuple[Union[User, list, None], DopError]: 
        """
        """

    @abstractmethod
    def delete_session(self, id: int) -> DopError: 
        """
        """

    @abstractmethod
    def delete_encrypted_session(self, session) -> DopError: 
        """   
        """


    @abstractmethod
    def delete_transaction(self, transaction_hash: str) -> DopError: 
        """
        """

    @abstractmethod
    def update_session(self, session_client, **kwargs) -> DopError: 
        """
        """



    @abstractmethod
    def update_encrypted_session(self, session, **kwargs) -> DopError: 
        """
        """ 

    @abstractmethod
    def update_or_create_encrypted_session(self, encSession: EncryptedSession) -> DopError:
        """
        """
    
    
    @abstractmethod 
    def create_encrypted_session(self, encSession: EncryptedSession) -> DopError:
        """
        """

    @abstractmethod
    def get_encrypted_session(self, where: dict = None) \
            -> Tuple[Union[EncryptedSession, list, None], DopError]: 
        """
        """


    @abstractmethod
    def get_product_summary(self, product_id) -> Tuple[dict, DopError]:
        """
        """

    @abstractmethod
    def get_product_details(self, product_id) -> Tuple[dict, DopError]:
        """
        """

    @abstractmethod
    def get_property(self, where: dict = None) \
            -> Tuple[Union[Property, list, None], DopError]:
        """
        """
    
    @abstractmethod
    def create_property(self, property: Property) -> Tuple[int, DopError]:
        """
        """

    @abstractmethod 
    def create_property_product(self, property_product: PropertyProduct) -> DopError:
        """
        """

    ########################################################
    # PURPOSE OF USAGE 
    ########################################################
    @abstractmethod
    def create_purpose_of_usage(self, 
                                purpose: PurposeOfUsage)\
                                -> Tuple[int, DopError]:
        """
        """

    @abstractmethod
    def get_purpose_of_usage(self,
                            where: dict = None) \
                            -> Tuple[Union[PurposeOfUsage, list, None], DopError]: 
        """
        """ 

    @abstractmethod
    def create_product_subscription(self, 
                                    subscription: ProductSubscription)  \
                                    -> Tuple[int, DopError]:
        """
        """

    @abstractmethod
    def get_product_subscription(self, 
                                where: dict = None)\
                                -> Tuple[Union[ProductSubscription, list, None], DopError]: 
        """
        """ 

    @abstractmethod
    def update_product_subscription(self, 
                                    subscription_id, 
                                    modified_entry: ProductSubscription) \
                                    -> DopError:
        """
        """

    @abstractmethod
    def delete_product_subscription(self, 
                                    subscriber_id, 
                                    subscription_id,
                                    product_id
                                    ) -> DopError:
        
        """
        """
    
    @abstractmethod
    def insert_account_role(self, account_role: AccountRole) \
                        -> Tuple[int, DopError ]:
        """
        """

    @abstractmethod
    def get_account_role(self, where:dict = {})\
                        -> Tuple[Union[AccountRole, list, None], DopError]:
        """
        """ 

    @abstractmethod
    def delete_account_role(self, id) -> DopError:
        """
        """
