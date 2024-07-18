#   SPDX-License-Identifier: Apache-2.0
#   © Copyright Ecosteer 2024

from typing import Tuple, Type, Union

from abc import ABC, abstractmethod
from common.python.error import DopError
from common.python.event import DopEvent
from provider.python.provider import Provider

class methodsPersistence(Provider):
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
    def cursor(self) -> Tuple[DopError, object]:
        """
        Return the database cursor so that the calling context can 
        execute operations using it 
        """


    @abstractmethod
    def execute_with_retry(self, query, values=None) -> Tuple[DopError, object]:
        """"""

    @abstractmethod 
    def serialize(resource, cursor):
        """"""

    @abstractmethod
    def sql_insert(self, table_name, obj: dict, ret_info: str="id") -> DopError:
        """"""

    @abstractmethod
    def sql_update(self, table_name, where: dict, update: dict) -> DopError:
        """"""

    @abstractmethod 
    def sql_select(self, base_query, where: dict = None, logic_op: str = 'AND', limit=-1, offset=-1) \
            -> Tuple[list, DopError]:
        """"""