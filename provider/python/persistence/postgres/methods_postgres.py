#   SPDX-License-Identifier: Apache-2.0
#   © Copyright Ecosteer 2024

import copy
import inspect
from functools import wraps
from inspect import currentframe, getframeinfo
import time
import traceback
import sys

import pyodbc
from typing import Tuple, Type, Union
 

from common.python.error import DopError
from provider.python.persistence.methods_persistence import methodsPersistence


class methodsPostgres(methodsPersistence):
    def __init__(self):
        super().__init__()
 
        self._config = None
        self._url = None
        self._connection = None

        self._recovery_delay_s = 5    #   delay in seconds that have to be waited for before recovery
        self._recovery_max = 10       #   maximum number of attempts to recover
        self._timeout = 5       # timeout in seconds for the connection setup and for the queries

    def init(self, config: str) -> DopError:
        self._config = config  
        return DopError() 

    def open(self) -> DopError:
        if self._connection != None:
            #   connected already (likely still ok)
            return DopError(0)
        sys.stdout.flush()
        max_retry = self._recovery_max
        while max_retry > 0:
            try:
                self._connection = pyodbc.connect(self._config, timeout = self._timeout)
                self._connection.autocommit = False
                self._connection.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
                self._connection.setencoding(encoding='utf-8')
            except Exception as e:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
                sys.stderr.flush()
                if isinstance(e, pyodbc.OperationalError) or isinstance(e, pyodbc.Error):
                    if self._recoverable(e):
                        max_retry -= 1
                        print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                            f"{getframeinfo(currentframe()).lineno} | Recovering from last error. Retries left: {max_retry}.\n", file = sys.stderr)
                        self._recovery_delay()
                        continue
                return DopError(99, "Non recoverable error while opening postgres communication module.") 
                
            return DopError(0, "Postgres provider opened.")
        return DopError(120, "Could not connect to the database: max number of attempts exceeded") 



    def close(self) -> DopError:
        if self._connection:
            self._connection.close()
            self._connection = None 
        return DopError()
        
    def begin_transaction(self) -> DopError:
        return DopError()

    def serialize(self, resource, cursor):
        response = {}
        if isinstance(resource, list):
            response = []
            for row in resource:
                response.append(self.serialize(row, cursor))
        else:
            if resource:
                for idx, value in enumerate(resource):
                    response[cursor.description[idx][0]] = value
        return response


    
    def cursor(self) -> Tuple[DopError, pyodbc.Cursor]:
        cursor = None
        max_retry = self._recovery_max      
        while max_retry > 0:       
            err = self.open()
            if err.isError():
                return err, None     
            try:
                cursor = self._connection.cursor()
            except Exception as e:
                if self._recoverable(e):
                    max_retry -= 1
                    print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                            f"{getframeinfo(currentframe()).lineno} | Recovering from last error. Retries left: {max_retry}.\n", file = sys.stderr)
                    self.close()
                    self._recovery_delay()
                    continue
                return DopError(123, "Non recoverable error while getting database cursor."), cursor  # not recoverable
            return DopError(0), cursor      # success
        return DopError(124,"Non recoverable error while getting database cursor: maximum number of attempts exceeded" ), cursor      


    
    def commit(self) -> DopError: 
        
        max_retry = self._recovery_max
        while max_retry > 0: # check exit condition
                
            err = self.open()
            if err.isError():
                return err

            try:
                self._connection.commit()
            except Exception as e:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                        f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)

                sys.stderr.flush()
                if isinstance(e, pyodbc.Error): 
                    if self._recoverable(e):
                        max_retry -= 1
                        print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                            f"{getframeinfo(currentframe()).lineno} | Recovering from last error. Retries left: {max_retry}.\n", file = sys.stderr)
                        self.close()
                        self._recovery_delay()
                        continue
                    return DopError(102, "Non recoverable error during commit.")

            return DopError()     
        return DopError(103, "Error during commit.")
        

    def rollback(self) -> DopError:
        max_retry = self._recovery_max
        while max_retry > 0: # check exit condition: if exception is not pyodbc.Error what happens
                
            err = self.open()
            if err.isError():
                return err

            try: 
                self._connection.rollback()
            except Exception as e:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                        f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)

                sys.stderr.flush()

                if isinstance(e, pyodbc.Error):
                    if self._recoverable(e):
                        max_retry -= 1 
                        print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                            f"{getframeinfo(currentframe()).lineno} | Recovering from last error. Retries left: {max_retry}.\n", file = sys.stderr)
                        self.close()
                        self._recovery_delay()
                        continue

                    return DopError(100, "Non recoverable error during rollback.")
            return DopError() # rollback was successful
        return DopError(101, "Error during rollback.")
        

    def _recoverable(self, e:Exception) -> bool:   
        exception_type: str = type(e).__name__
        #print("REC TYPE: " + exception_type)
        #print("REC CODE: " + e.args[0])
        if exception_type == "OperationalError":
            if e.args[0]=='08001' or e.args[0] == '08S01':             
                return True
        if exception_type == "Error":
            if e.args[0]=='57P01' or e.args[0] == 'HY000':
                return True  
        return False

    
    def _recovery_delay(self):
        time.sleep(self._recovery_delay_s)

    
    def sql_insert(self, table_name, obj: dict, ret_info: str= "id") -> DopError:
        query = f"INSERT INTO {table_name} "
        cols = []
        values = []
        params = []
        for attribute, value in obj.items():
            #if value: # this statement does not allow to insert or set values to False, 0, or '' 
            if value is not None: # value can be False or 0 or '' 
                cols.append(attribute)
                params.append('?')
                values.append(value)
        cols = ' (' + ", ".join(cols) + ')'
        params = ' (' + ', '.join(params) + ')'
        query += f"{cols} VALUES {params}"
        query += f' RETURNING {ret_info};'
        try:
            err, cursor = self.execute_with_retry(query, values)
       
        except Exception as e: 
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()

            return None, DopError(110, "An exception occurred during insert operation.")

        if err.isError():
            return None, err
        
        _id = cursor.fetchall()

        return _id[0][0], err

    def sql_update(self, table_name, where: dict, update: dict) \
        -> DopError:
        values = []
        _set = []
        _where = []
        for key, value in update.items():           
            #if value:
            if value is not None:
                values.append(value)
                _set.append('{key} = ?'.format(key=key))
        for attribute, value in where.items():
            #if value:
            if value is not None:
                _where.append(f'{attribute}=?')
                values.append(value)
            else:
                return DopError(1)
        if len(values) == 0:
            return DopError(0, "No update requested")
        try:
            query = f'UPDATE {table_name} SET ' \
                + ','.join(_set) +  \
                ' WHERE ' + ' AND '.join(_where)
            c = self._connection.cursor()

            err, cursor = self.execute_with_retry(query, values)
            if err.isError():
                return err
            
        except Exception as e:
            if e.args and len(e.args) > 0:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                        f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
                sys.stderr.flush()
                return DopError(109, "An exception occurred during update operation: impossible to update the element.")
            return DopError(109, "An exception occurred during update operation: impossible to update the element.")
        return DopError()

    def sql_select(self, base_query, where: dict = None, logic_op: str = 'AND', limit=-1, offset=-1) \
            -> Tuple[list, DopError]:
      
        query = base_query

        values = []
        _where = []
        if where:
            for attribute, value in where.items():
                #if value:
                if value is not None:
                    _where.append(f'{attribute}=?')
                    values.append(value)
            where_clause = f' {logic_op} '.join(_where)
            query += f" WHERE {where_clause}"

        if limit != -1 and offset != -1:
            query += f" LIMIT {limit} OFFSET {offset} "

        err, cursor = self.execute_with_retry(query, values)
        if err.isError():
            return [], DopError(106, "An error occurred while executing a select query.")
        try:
            row = cursor.fetchall()
            data = self.serialize(row, cursor)

        except Exception as e:
            if e.args and len(e.args) > 0:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                        f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
                sys.stderr.flush()
                return [], DopError(107, "An exception occurred while extracting data from the result set.")
            return [], DopError(107,
                             "An exception occurred while extracting data from the result set.")

        return data, DopError()

    def execute_with_retry(self, query, values=None) -> Tuple[DopError, pyodbc.Cursor]:
        # values - tuple (value1, value2, ) 
        max_retry = self._recovery_max
        cursor = None
        while max_retry > 0: 
            err = self.open()
            if err.isError():
                return err, cursor
            err, cursor = self.cursor() 

            if err.isError():
                return err, cursor
            
            try:
                cursor.execute(str(query), values)
                 
            except pyodbc.Error as e: 
                debug_stmt = f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                            f"{getframeinfo(currentframe()).lineno} |"
                
                if self._recoverable(e):
                    max_retry -= 1
                    print(f"{debug_stmt}| Recovering from last error. Retries left: {max_retry}.\n", file = sys.stderr)
                    self.close()
                    self._recovery_delay()
                    continue
                print(f"{debug_stmt}| Error: {e}\n", file = sys.stderr)
                    
                return DopError(121, "Non recoverable error while executing a query."), cursor # not recoverable
            
            return DopError(0), cursor    #  success
        
        return DopError(122, "Query could not be executed: maximum number of attempts exceeded."), cursor

