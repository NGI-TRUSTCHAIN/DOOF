#   © Copyright Ecosteer 2024

from typing import Tuple, List
import json

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload
from common.python.new_processor_env import ProcessorEnvs
from common.python.threads import DopStopEvent
from common.python.utils import DopUtils
from common.python.model.models import User

from provider.python.persistence.postgres.methods_postgres import methodsPostgres


class DexChangePasswordProcessor(ProcessorProvider):
    
    def __init__(self):
        super().__init__()
        self._config = ""
        self._event_type = {"dex_change_password"}
        self._psql = methodsPostgres() 
        self._acc_table_name = "ext_account_repo"
    
    def init(self, config: str) -> DopError:
        """
        The configuration is the connection string that configures the connectivity with the 
        database 
        """
        self._config = config 
        self._psql.init(config) 
        return DopError()
    
    
    def open(self) -> DopError:
        self._psql.open()
        return DopError() 
    
    
    def close(self) -> DopError:
        self._psql.close()
        return DopError() 
    
    
    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) -> DopError:
        """
        dex_change_password 
        {
            "session":"",
            "task":"",
            "event":"dex_change_password",
            "params":  {
                "auth_token": ""
            }
        }     
        """
        
        if event.header.event in self._event_type:
           
            out = self._handle_event(event, envs)
            # NOTE if there is an error, the processing is interrupted and 
            # any other events left in the stack are emptied by the worker
            if out.isError():
                return out 
            
        return DopError()
    
    def _handle_event(self, event: DopEvent, envs: ProcessorEnvs) -> DopError:
        
        blk = envs.blk_provider
        db = envs.db_provider
        logger = envs.logger_provider 
        phase = 1 

        header = event.header
        payload = event.payload.to_dict()
        
        old_pwd = payload.get('old_password', None)
        new_pwd = payload.get('new_password', None)

        if old_pwd is None or new_pwd is None:
            envs.events.push(header.event, DopEvent(header, DopEventPayload(
                {
                    "err": 1,
                    "phase": phase,
                    "old_password": None, 
                    "new_password": None
                }
            )))
            return DopError()
        
        if new_pwd == '': 
            # empty string not supported 
            envs.events.push(header.event, DopEvent(header, 
                DopEventPayload({
                    "err": 1,
                    "phase": phase,
                    "old_password": "*", 
                    "new_password": ""
            })))
        
        # get authenticated user from stack 
        try:
            user = envs.data.get(User.__name__)[0]
        except:
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND) 
            return err

        # check correctness of old password
        if old_pwd != '':
            # backwards compatibility: dev envs do not have pwd 
            old_hash = DopUtils.sha256(old_pwd)
    
        else: 
            old_hash = ''     

        query = f"""SELECT password from {self._acc_table_name}"""
        where = {"username": user.username}

        res, _err = self._psql.sql_select(query, where)
        if _err.isError():
            return _err 

        if res is None or len(res) == 0:
            return DopError() 

        if isinstance(res, list): 
            res = res[0]

        if old_hash != res.get('password'):
            envs.events.push(header.event, DopEvent(header, 
                DopEventPayload({
                    "err" : DopUtils.ERR_PL_NOT_AUTHORIZED['id'],
                    "phase" : phase
                })                                    
                ))
            return DopError()
        
        
        err = self._psql.begin_transaction()   
        
        # compute hash of new password and update the table
        new_hash = DopUtils.sha256(new_pwd)
        update = {'password' : new_hash}
        _err = self._psql.sql_update(self._acc_table_name, where, update)

        if _err.isError():
            self._psql.rollback() 
            return _err 
        
        self._psql.commit() 
        envs.events.push(header.event, DopEvent(
            header, DopEventPayload({
                "err": 0, 
                "phase": 1
            })
        ))

        return DopError()