#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   ver:    1.1
#   date:   14/06/2023
#   author: georgiana-bud

# VERSION 1.1 
# - added imports in try - except block for usage of module in different deployments

"""
Minimalistic implementation of platform's utils

"""
import base64
import builtins
import datetime
import sys
import os
import yaml
import importlib
import importlib.util
import traceback
from uuid import UUID 

from importlib.machinery import SourceFileLoader
from importlib.machinery import SourcelessFileLoader


from typing import Tuple, Callable

from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload

from common.python.config_utils import ConfigUtils

import datetime
import hashlib 
import time
from functools import wraps
import binascii
 
#   the following imports are to support the load_provider static method
#   import all the ABC base classes (base classes for any provider to be loaded using DopUtil.load_configuration)
#import provider.python.intermediation.monitor.provider_monitor
#import provider.python.presentation.output.provider_pres_output
#   import provider.presentation.input.provider_pres_input
#   etc.


class DopUtils:

    
    MSG_INVALID_TOKEN = 'Invalid Token'
    MSG_TOKEN_REQUIRED = 'Authentication Required'
    MSG_USER_NOT_FOUND = 'Token contained no recognizable user'
    MSG_SERVER_ERROR = 'Server error'
    MSG_SESSION_EXPIRED = 'Session expired'


    MSG_ADDRESS_ERROR = 'Impossible to get user address'
    MSG_PRODUCT_NOT_FOUND = 'Impossible to find the product'
    MSG_PRODUCT_ADDR_NOT_FOUND = 'Impossible to get the product address'
    MSG_NOT_AUTHORIZED = 'User action not authorized'

    # NEW MESSAGES WITH IDS FOR REFACTORED LOGS
    MSG_SIGNUP_OK = {
        "id" : 1, 
        "msg" : "Successfully signup! New account created."
    }
    MSG_DEPLOYING = {
        "id" : 2, 
        "msg" : "Deploying the contract."
    }
    MSG_DEPLOY_OK = {
        "id" : 3,
        "msg" : "Contract Successfully Deployed."
        }
    MSG_REQ_SUB = {
        "id" : 4,
        "msg" : "Request for subscription sent."
    }
    MSG_REQ_UNSUB = {
        "id" : 5,
        "msg" : "Request for unsubscribe sent."
    }
    MSG_REQ_DEPOSIT = {
        "id" : 6,
        "msg" : "Request to deposit sent."
    }
    MSG_REQ_GRANT = {
        "id" : 7,
        "msg" : "Request to set grant sent."
    }
    MSG_REQ_REVOKE = {
        "id" : 8,
        "msg" : "Request to revoke sent."
    }
    MSG_DEPOSIT_OK = {
        "id" : 9,
        "msg" : "Deposit successful."
    }
    MSG_GRANT_OK = {
        "id":  10,	
        "msg": "Grant operation successfully completed."
    }
    MSG_REVOKE_OK = {
        "id": 11,
        "msg": "Revoke operation successfully completed."
    }
    MSG_SUBSCRIBE_OK ={
        "id": 12,
        "msg": "Subscribe operation successfully completed."
    }
    MSG_UNSUBSCRIBE_OK = {
        "id": 13,	
        "msg": "Unsubscribe operation successfully completed."
    }

    MSG_NEW_SESSION = {
        "id":14, 
        "msg": "New session created"
    }

    
    MSG_NEW_ENC_SESSION = {
        "id":15, 
        "msg": "New encrypted session created"
    }

    # PL: Persitence Layer
    
    ERR_PL_USER_EXISTS     =   {"id" : 500, "msg": "User already exist"}   # db related
    ERR_PL_SIGNUP      =   {"id" : 501, "msg": "An error occurred during signup (persistence layer)"}  # db related
    ERR_PL_UNAME_PWD   =   {"id" : 502, "msg": "Username or Password error"}   # db related
    ERR_PL_USER_NOT_FOUND  =   {"id" : 503, "msg": "User not found"}               # db related
    ERR_PL_SESSION_NOT_CREATED = {"id" : 504, "msg": "Session not created"}        # db related
    ERR_PL_ENC_SESSION_NOT_CREATED = {"id" : 505, "msg": "Encrypted session not created"}  # db related
    ERR_PL_TRANSACT_NOT_FOUND  = {"id" : 506, "msg": "Transaction not found"}      # db related
    
    ERR_PL_LOOK_ACC    =   {"id" : 507, "msg": "Cannot lookup account"}        # db related
    ERR_PL_LOOK_SC    =    {"id" : 508, "msg": "Cannot lookup smart contract"} # db related
    ERR_PL_USER_NOT_SUBSCRIBED = {"id" : 509, "msg": "User not subscribed"}        # db related
    ERR_PL_GRANT       =   {"id" : 510, "msg": "An error occurred during grant request."}  # exception + db related --> split in two errors
    ERR_PL_REVOKE      =   {"id" : 511, "msg": "An error occurred during revoke request."} # exception + blk related + db related --> split in 3 errors
    ERR_PL_SUB          = {"id" : 512, "msg": "An error occurred during subscription request"} # exception + blk related + db related --> split in 3 errors
    ERR_PL_PRODUCT_NOT_FOUND    = {"id" : 513, "msg": "Impossible to find the product"}    # db related
    ERR_PL_SESSION_NOT_FOUND       = {"id" : 514, "msg": "Session not found"}      # db related    
    ERR_PL_TRANSACT_SAVE    =  {"id" : 515, "msg": "Error during transaction saving"}      # db related
    ERR_PL_NOT_AUTHORIZED   =  {"id" : 516, "msg": "User action not authorized"}           # db related
    ERR_PL_PROD_REF        =   {"id" : 517, "msg": "Impossible to get the product reference"}  # internal check + db related --> split in 2 errors
    ERR_PL_PROD_SUB    =       {"id" : 518, "msg": "Impossible to get the product subscribers"}    # db related
    ERR_PL_PROD_QUERY   =      {"id" : 519, "msg": "Impossible to retrieve products"}  # db related
    ERR_PL_SESSION_NOT_PRESENT    = {"id" : 520, "msg" : "Session not found. Login required"}  # db related
    ERR_PL_INVALID_TOKEN      = {"id" : 521, "msg" : "Invalid Token"}      # db related
    ERR_PL_AUTHENTICATION_REQUIRED     = {"id" : 522, "msg" : "Authentication required"}    # db related
    ERR_PL_SESSION_TOKEN      = {"id" : 523, "msg" : "This session is not valid for this token"}   # db related
    ERR_PL_SESSION_1           = {"id" : 524, "msg" : "Session error 1"}       # db related
    ERR_PL_SESSION_2           = {"id" : 525, "msg" : "Session error 2"}       # db related
    ERR_PL_DEPOSIT     =   {"id" : 526, "msg": "An error occurred during deposit request"} # divided in 3 cases: 1 for monitor processor, 1 blk related and 1 db related
    ERR_PL_DEPLOY      =   {"id" : 527, "msg": "Impossible to deploy the contract"}    # divided in 3 cases: 1 for monitor processors, 1 blk related and 1 db related 
    


    # TODO change to ERR_PL_SESSION_MLE_LOOKUP
    ERR_SESSION_MLE_LOOKUP = {"id": 528, "msg": "Error in getting the all the sessions of this user."}
    ERR_PL_SUBSCRIPTION = {"id": 529, "msg": "Impossible to retrieve subscription."}
    ERR_PL_SUBSCRIPTION_NOT_FOUND = {"id": 530, "msg": "Subscription not found."}
    ERR_PL_PURPOSE_NOT_FOUND = {"id": 531, "msg": "Purpose of usage not found."}
    ERR_PL_ROLE_C         = {"id": 532, "msg": "Impossible to create new account role."}
    ERR_PL_ROLE_NOT_FOUND         = {"id": 533, "msg": "Impossible to retrive account role."}
    ERR_PL_ROLE_R         = {"id": 534, "msg": "Impossible to delete account role."}
    ERR_PL_TRANSACT_DEL =   {"id": 535, "msg": "Error during transaction deletion."}

    ERR_PL_SERVICE_NOT_FOUND = {"id": 536, "msg": "Service not found."}
    ERR_PL_CONV_C = {"id": 537, "msg": "Impossible to create token conversion entry."}

    ERR_PL_USER_UPDATE = {"id": 538, "msg": "Error when updating user information."}

    ERR_PL_SUBSCRIPT_UPDATE = {"id": 539, "msg": "Error updating subscription information"}
    # IP: Intermediation platform
    ERR_IP_SIGNUP  =   {"id" : 601, "msg": "An error occurred during signup request (intermediation platform)"}    # blk related
    ERR_IP_LOOK_WALLET =   {"id" : 602, "msg": "Cannot lookup wallet balance"} # blk related
    ERR_IP_GRANT = {"id" : 603, "msg": "Impossible to give the grant. Check the subscriber balance."}  # blk related 
    ERR_IP_REVOKE  =   {"id" : 604, "msg": "An error occurred during revoke request."} # exception + blk related + db related --> split in 3 errors
    ERR_IP_SUB     = {"id" : 605, "msg": "An error occurred during subscription request"} # exception + blk related + db related --> split in 3 errors
    ERR_IP_UNSUB         = {"id" : 606, "msg": "An error occurred during unsubscription request"} # exception + blk related --> split in 2 errors
    ERR_IP_DEPOSIT     =   {"id" : 607, "msg": "An error occurred during deposit request"} # divided in 3 cases: 1 for monitor processor, 1 blk related and 1 db related
    ERR_IP_DEPLOY      =   {"id" : 608, "msg": "Impossible to deploy the contract"}    # # divided in 3 cases: 1 for monitor processors, 1 blk related and 1 db related
    
    ERR_IP_ACCOUNT = {"id": 609, "msg":"Impossible to get the account info."}
    ERR_IP_SUBSCRIPTION = {"id": 610, "msg": "Impossible to retrieve subscription info."}

    # OTHER
    ERR_USER_ADDRESS = {"id" : 801, "msg": "Impossible to get user address"}   # internal checks based on info from db
    ERR_CIPHER_SUITE  = {"id" : 802, "msg": "Cipher_suite not valid"}       # internal
    ERR_LEN_KEY     =   {"id" : 803, "msg": "Length of key not valid"}      # internal
    ERR_DEPLOY      =   {"id" : 804, "msg": "Impossible to deploy the contract"}    # # divided in 3 cases: 1 for monitor processors, 1 blk related and 1 db related
    ERR_DEPOSIT     =   {"id" : 805, "msg": "An error occurred during deposit request"} # divided in 3 cases: 1 for monitor processor, 1 blk related and 1 db related
    ERR_GRANT_GENERIC = {"id" : 806, "msg": "An error occurred during grant request."}
    ERR_REVOKE_GENERIC  =   {"id" : 807, "msg": "An error occurred during revoke request."} # exception + blk related + db related --> split in 3 errors
    ERR_SUB_GENERIC           = {"id" : 808, "msg": "An error occurred during subscription request"} # exception + blk related + db related --> split in 3 errors
    ERR_UNSUB_GENERIC          = {"id" : 809, "msg": "An error occurred during unsubscription request"} # exception + blk related --> split in 2 errors
    ERR_EVENT_NOT_FOUND   = {"id" : 810, "msg": "Event not found"}          # internal check
    ERR_OPERATION          = {"id" : 811, "msg": "Operation error"}       # ?
    MSG_NEED_INFO               = {"id" : 812, "msg": "Please supply all the necessary information for the requested operation."}   # internal checks
    ERR_PRODUCT_ADDR_NOT_FOUND = {"id" : 813, "msg": "Impossible to get the product address"}   # internal check based on info from db
    ERR_PROD_REF        =   {"id" : 814, "msg": "Impossible to get the product reference"}  # internal check + db related
    ERR_CIPHER_SUITE_QUERY = {"id": 815, "msg": "Error in processing cipher_suite_query"}   # internal checks
    ERR_SERVER       = {"id" : 816, "msg" : "Server error"}       # exception
    ERR_SESSION_EXPIRED    = {"id" : 817, "msg" : "Session expired"}    # internal check based on db info
    ERR_REQ_PROCESSING      = {"id" : 818, "msg" : "An error occurred while processing your request"}   # exception/internal checks
    ERR_REQ_PROCESSING_GENERIC = {"id" : 819, "msg" : "An error occurred while processing a request"}   # exception/internal checks

    ERR_GENERIC = {"id": 820, "msg": "An error has occurred"}
 

    ERR_JSON = {"id": 821, "msg":"Error in converting the received event to JSON"} # not returned to user but logged
    ERR_SESSION_REQ = {"id": 822, "msg": "Event missing 'session' field"}
    ERR_EVENT_REQ = {"id": 823, "msg": "Event missing 'event' field"}
    ERR_UNRECOGNIZED_EVENT = {"id": 824, "msg": "Unrecognized input event"}

    ERR_AUTHENTICATION_REQUIRED = {"id": 825, "msg": "Authentication required"}
    ERR_SESSION_REQUIRED = {"id": 826, "msg": "Session required"}

    ERR_TOKEN_HEX = {"id": 827, "msg": "The token can contain only hex chars"}
    ERR_SESSION_HEX = {"id": 828, "msg": "The session can contain only hex chars"}

    ERR_PARAMS_REQUIRED = {"id": 829, "msg": "Event missing 'params' field."}

    ERR_OP_NOT_PERMITTED = {"id": 830, "msg": "Operation not permitted. You may not have enough privileges."}
    
    ERR_PRODUCT_RANGE = {"id": 831, "msg": "Price or period are not valid"}
    ERR_MISS_SUBSCRIPTION = {"id": 832, "msg": "Event missing subscription id"}
    ERR_MISS_VALUE = {"id": 833, "msg": "Event missing value"}
    ERR_INVALID_VALUE = {"id": 834, "msg": "Invalid value"}
    ERR_MISS_PROD = {"id": 835, "msg": "Event missing product id"}
    ERR_MISS_LABEL = {"id": 836, "msg": "Event missing product label"}
    ERR_MISS_PURPOSE = {"id": 837, "msg": "Event missing purpose id"}
    ERR_TYPE = {"id": 838, "msg": "Query type not supported"}

    ERR_MISS_PARAMS = {"id": 839, "msg": "Event missing mandatory parameters."}

    ERR_SESSION_FORMAT = {"id": 840, "msg": "Session is malformed."} 

    ERR_INSUFF_FUNDS = {"id": 841, "msg": "Cannot complete operation due to insufficient funds."}

    MAX_AGE = 43200




    
    @staticmethod 
    def create_dop_error(err: dict):
        """Take as input the constants defined in this class"""
        return DopError(err['id'], err['msg'])
  


    @staticmethod
    def config_to_dict(connstring: str) -> Tuple[DopError,dict]:
        return ConfigUtils.config_to_dict(connstring)

    @staticmethod
    def config_get_string(config: dict, keys: list, default_value: str) -> Tuple[bool, str]:
        return ConfigUtils.config_get_string(config, keys, default_value)
        
    @staticmethod
    def config_get_int(config: dict, keys: str, default_value: int) -> Tuple[bool, int]:
        return ConfigUtils.config_get_int(config, keys, default_value)


    @staticmethod
    def parse_yaml_configuration(confile: str) -> Tuple[DopError,dict]:
        conf: dict = {}
        #   check if file exists
        if os.path.exists(confile) == False:
            return (DopError(101,'Configuration file does not exist'), conf)

        with open(confile,'r') as stream:
            try:
                conf = yaml.safe_load(stream)
                return (DopError(),conf)
            except yaml.YAMLError as exc:
                if hasattr(exc, 'problem_mark'):
                    mark = exc.problem_mark
                    msg =  f"Error in parsing configuration file: position ({(mark.line+1)}:{(mark.column+1)})"
                    return (DopError(103,msg),conf)
                return(DopError(3,"conf file parsing error"),{})

    @staticmethod
    def load_provider(config: dict, available=False) -> Tuple[DopError, Callable]:
        """
        Return a new provider given the configuration options as
        {
            'path':'/home/ecosteer/monitor/ecosteer/dop/provider/presentation/output/pres_output_rabbitqueue.py',
            'class':'outputRabbitQueue',
            'configuration':'url=amqp://guest:guest@deb10docker:5672/;queue_name=imperatives;rc=10;rd=10;dm=1;'
        }
        """
        
        if ('path' in config) == False:
            return (DopError(1,"configuration missing [path] key"),None)

        if ('configuration' in config) == False:
            return (DopError(2,"configuration missing [configuration] key"),None)
        

        has_class = ('class' in config)
        has_provider = ('provider' in config)
        if (has_class or has_provider) == False:
            return (DopError(3,"configuration missing class key"),None)

        conf_path: str = config['path']
        conf_provider: str = config['provider'] if has_provider else config['class']


        try: 
            #   NOTE:
            #   the class name is used as if it were a module.name, too
            #   -   as long as no different modules implements classes with the same name, this should do
            if not available:
                module = SourceFileLoader(conf_provider, conf_path).load_module()
                provider = getattr(module, conf_provider)
            else: 
                #provider = eval(conf_provider)
                #provider = globals()[conf_provider]
                try:
                    provider = builtins.providers[conf_provider]
                except Exception as e:
                    # Two cases: 
                    # - builtins does not have 'providers' attribute (AttributeError)
                    # - conf_provider is not a key of builtins.providers
                    return (DopError(121, "Provider indicated as available but not present in builtins"), None)
            return (DopError(),provider())
        except FileNotFoundError as fe:
            return (DopError(120, "Provider source file not found."), None)
        except ValueError as ve:
            print(str(ve))
            module = SourcelessFileLoader(conf_provider, conf_path).load_module()
            provider = getattr(module, conf_provider)
            return (DopError(),provider())
        except Exception as e:
            print(str(e))
            print(traceback.format_exc())
            return (DopError(4,"exception while loading provider"),None)


        
#        try:
#            module = importlib.import_module(conf_module)
#            provider = getattr(module, conf_provider)
#            return (DopError(),provider())
#        except:
#            return (DopError(11,"exception while loading provider"),None)

    @staticmethod 
    def to_base64(input: str) -> Tuple[str, DopError] :
        if len(input) == 0: 
            return "", DopError(1, "empty string")
        try:
            input_bytes = input.encode()
            input_bytes_b64 = base64.standard_b64encode(input_bytes)
            input_b64 = input_bytes_b64.decode()
            return input_b64, DopError(0)
        except Exception as e:
            return "", DopError(2, "exception during base64 transformation")

    @staticmethod
    def from_base64(input: str) -> Tuple[str, DopError]:
        if len(input) == 0: 
            return "", DopError(1, "empty string")
        try:
            input_bytes_b64 = input.encode() 
            input_bytes = base64.standard_b64decode(input_bytes_b64)
            return input_bytes.decode(), DopError
        except Exception as e:
            return "", DopError(2, "exception during base64 transformation")



    @staticmethod
    def create_uuid() -> UUID:
        import uuid 
        return uuid.uuid4()

    @staticmethod 
    def list_event_types(self, events: list) -> list:
        types = []
        for ev in events: 
            types.append(ev.header.event)
        
        return types


    @staticmethod
    def serialize_datetime(obj):
    
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, dict): 
            for k in obj:
                if isinstance(obj[k], datetime.datetime):
                    obj[k] = obj[k].isoformat()
        elif isinstance(obj, list):
            for el in obj:
                if isinstance(el, dict):
                    for k in el:
                        if isinstance(el[k], datetime.datetime):
                            el[k] = el[k].isoformat()
        
        return obj

    @staticmethod
    def create_auth_token() -> str:
        """
        Create an uuid which will be used as auth_token
        """
        import uuid
        return uuid.uuid4().hex
    


    @staticmethod
    def _session_required(event: DopEvent, db):
        session = event.header.session
        if session is None:
            return DopUtils.create_dop_error(DopUtils.ERR_AUTHENTICATION_REQUIRED)

        try:
            session, perr = db.get_session({'value': session})
            if not session or perr.isError():
                err = DopUtils.create_dop_error(DopUtils.ERR_PL_INVALID_TOKEN)
                err.perr = perr
                return err
        except Exception as e:
            return DopUtils.create_dop_error(DopUtils.ERR_PL_INVALID_TOKEN)
        return DopError()

    @staticmethod
    def _tx_hash_required(event: DopEvent, db, attribute):
        hash = event.payload.to_dict().get(attribute, None)
        if hash is None:
            # TODO maybe some error related to transaction
            return DopUtils.create_dop_error(DopUtils.ERR_AUTHENTICATION_REQUIRED) 
        try:
            transaction, perr = db.get_transaction({'hash': hash})
            if perr.isError():
                # TODO refrase the following errors, should be something with transaction
                err = DopUtils.create_dop_error(DopUtils.ERR_PL_INVALID_TOKEN)
                err.perr = perr
                return err
        except Exception as e:
            return DopUtils.create_dop_error(DopUtils.ERR_PL_INVALID_TOKEN)
        return DopError()


    @staticmethod
    def check_session(event: DopEvent, db):
        """
        Checks if the session is valid
        1. the session is inside the event
        2. the session contains only hex chars
        :param event: Event object
        :param db: database object
        :return:
        """

        # the session is inside the event
        session = event.header.session
        if session is None:
            return DopUtils.create_dop_error(DopUtils.ERR_SESSION_REQUIRED)

        # the token contains only hex chars
        tmp_session = session.replace('-', '')
        try:
            int(tmp_session, 16)
        except ValueError:
            return DopUtils.create_dop_error(DopUtils.ERR_SESSION_HEX)

        return DopError()


    @staticmethod
    def check_token(event: DopEvent, db):
        """
        Checks if the auth token is a valid token:
        1. the token is inside the event
        2. the token contains only hex chars
        :param event: Event object
        :param db: database object
        :return:
        """

        # the token is inside the event
        token = event.payload.to_dict().get('auth_token', None)
        if token is None:
            return DopUtils.create_dop_error(DopUtils.ERR_AUTHENTICATION_REQUIRED)

        # the token contains only hex chars
        try:
            int(token, 16)
        except ValueError:
            return DopUtils.create_dop_error(DopUtils.ERR_TOKEN_HEX) 

        return DopError()

    @staticmethod    
    def is_session_expired(session) -> bool:
        now = datetime.datetime.utcnow()
        difference = (now - session.last_updated).total_seconds()
        if difference > DopUtils.MAX_AGE:
            # expired
            return True
        return False

    @staticmethod
    def get_random_string(length):
        # TODO Generate password with sys
        """
        Return a securely generated random string.
        """
        return binascii.hexlify(os.urandom(length)).decode()

    @staticmethod  
    def make_random_password(length=10):
        """
        Generate a random password with the given length
        """
        return DopUtils.get_random_string(length)
 
    @staticmethod  
    def hash_string(string: str):
        salt = hashlib.sha3_256(os.urandom(60)).hexdigest().encode('ascii')
        pwdhash = hashlib.pbkdf2_hmac('sha512',
                                    string.encode('utf-8'),
                                    salt,
                                    100000)
        pwdhash = binascii.hexlify(pwdhash)
        return (salt + pwdhash).decode('ascii')

    @staticmethod  
    def verify_hash(hash: str, string: str) -> bool:
        salt = hash[:64]
        hash_password = hash[64:]
        pwdhash = hashlib.pbkdf2_hmac('sha512',
                                    string.encode('utf-8'),
                                    salt.encode('ascii'),
                                    100000)
        pwdhash = binascii.hexlify(pwdhash).decode('ascii')
        return pwdhash == hash_password

    @staticmethod 
    def sha256(string: str) -> str:
        str_b = string.encode('utf-8')
        m = hashlib.sha256()
        m.update(str_b)
        r = m.hexdigest() 
        return r

    
    @staticmethod 
    def sha3_256(string: str) -> str:
        str_b = string.encode('utf-8')
        m = hashlib.sha3_256()
        m.update(str_b)
        r = m.hexdigest() 
        return r

    @staticmethod
    def log_params(_type, msg):
        return {
            'log_obj': {
                'type': _type,
                'msg': msg
            }
        }

    @staticmethod
    def auth_required():
        """
        Decorator Checks if:
        1) The token is inside the event
        2) Session is inside the event
        3) Token contains only hex chars/home/pietro/Documents/projects/ecosteer/marketplace-client/app/src/views/404.vue
        4) Session contains only hex chars and '-'
        5) The token exists inside the database and it corresponds to the correct session
        6) session is not expired
        """

        def wrapper(fn):
            @wraps(fn)
            def decorator(*args, **kwargs):
                event = args[1]
                envs = args[2]
                db = envs.db_provider
                error = DopUtils.check_token(event, db)
                if error.isError():
                    payload = DopEventPayload(DopUtils.log_params('error', DopUtils.ERR_AUTHENTICATION_REQUIRED['msg']))
                    response_header = DopEventHeader(
                        event.header.session,
                        event.header.task,
                        DopEvent.LOG)
                    event = DopEvent(response_header, payload)
                    return [(event, error)]
                error = DopUtils.check_session(event, db)
                if error.isError():     
                    payload = DopEventPayload(DopUtils.log_params('error', DopUtils.ERR_SESSION_REQUIRED['msg'])) 
                    response_header = DopEventHeader(
                        event.header.session,
                        event.header.task,
                        DopEvent.LOG)
                    event = DopEvent(response_header, payload)
                    return [(event, error)]
                # the token is inside the database and is associated
                # with the correct session
                token = event.payload.to_dict().get('auth_token', None)
                try:
                    session, perr = db.get_session(where={'token': token,
                                                        'value': event.header.session},
                                                )
                    if perr.isError():
                        err = DopUtils.create_dop_error(DopUtils.ERR_PL_SESSION_TOKEN)
                        err.perr = perr
                        payload = DopEventPayload(DopUtils.log_params('error', err.msg)) # TODO Also: session not found. Login required.
                        response_header = DopEventHeader(
                            event.header.session,
                            event.header.task,
                            DopEvent.LOG)
                        event = DopEvent(response_header, payload)
                        return [(event, err)]
                except Exception as e:
                    err = DopUtils.create_dop_error(DopUtils.ERR_SERVER)
                    payload = DopEventPayload(DopUtils.log_params('error', err.msg))
                    response_header = DopEventHeader(
                        event.header.session,
                        event.header.task,
                        DopEvent.LOG)
                    event = DopEvent(response_header, payload)
                    return [(event, err)]
                
                # Check that the session is not expired
                if DopUtils.is_session_expired(session):
                    # may also check if there is an encrypted_session linked to this session 
                    # if not, 0 rows are deleted
                    perr = db.delete_encrypted_session(session.id)
                    if perr.isError():
                        err = DopUtils.create_dop_error(DopUtils.ERR_PL_SESSION_1)
                        err.perr = perr
                        payload = DopEventPayload(DopUtils.log_params('error', err.msg))
                        response_header = DopEventHeader(
                            event.header.session,
                            event.header.task,
                            DopEvent.LOG)
                        event = DopEvent(response_header, payload)
                        return [(event, err)]
                    perr = db.delete_session(session.id)
                    if perr.isError():
                        err = DopUtils.create_dop_error(DopUtils.ERR_PL_SESSION_2)
                        err.perr = perr
                        payload = DopEventPayload(DopUtils.log_params('error', err.msg))
                        response_header = DopEventHeader(
                            event.header.session,
                            event.header.task,
                            DopEvent.LOG)
                        event = DopEvent(response_header, payload)
                        return [(event, err)]                    
                    err = DopUtils.create_dop_error(DopUtils.ERR_SESSION_EXPIRED)
                    payload = DopEventPayload(DopUtils.log_params('error', err.msg))
                    response_header = DopEventHeader(
                        event.header.session,
                        event.header.task,
                        DopEvent.LOG)
                    event = DopEvent(response_header, payload)
                    return [(event, DopError(0))]
                return fn(*args, **kwargs)

            return decorator

        return wrapper

    @staticmethod
    def check_transaction():
        def wrapper(fn):
            @wraps(fn)
            def decorator(*args, **kwargs):
                event = args[1]
                envs = args[2]
                db = envs.db_provider
                error = DopUtils._tx_hash_required(event, db, attribute='transaction_id')
                if error.isError():     
                    # TODO check this - should be "transaction id missing" or something similar
                    payload = DopEventPayload(DopUtils.log_params('error', DopUtils.ERR_AUTHENTICATION_REQUIRED['msg']))  
                    response_header = DopEventHeader(
                        event.header.session,
                        event.header.task,
                        DopEvent.LOG)
                    event = DopEvent(response_header, payload)
                    return [(event, error)]
                return fn(*args, **kwargs)

            return decorator

        return wrapper


    @staticmethod
    def session_is_valid():
        """
        Decorator Checks only if the session is not expired
        """

        def wrapper(fn):
            @wraps(fn)
            def decorator(*args, **kwargs):
                event = args[1]
                envs = args[2]
                db = envs.db_provider
                try:
                    session, perr = db.get_session(
                        where={'value': event.header.session})
                    if perr.isError():
                        err = DopUtils.create_dop_error(DopUtils.ERR_PL_SESSION_NOT_FOUND)
                        err.perr = perr
                        payload = DopEventPayload(DopUtils.log_params('error', err.msg))
                        response_header = DopEventHeader(
                            event.header.session,
                            event.header.task,
                            DopEvent.LOG)
                        event = DopEvent(response_header, payload)
                        return [(event, err)]
                except Exception as e:
                    err = DopUtils.create_dop_error(DopUtils.ERR_SERVER)
                    payload = DopEventPayload(DopUtils.log_params('error', err.msg))
                    response_header = DopEventHeader(
                        event.header.session,
                        event.header.task,
                        DopEvent.LOG)
                    event = DopEvent(response_header, payload)
                    return [(event, err)]
                if DopUtils.is_session_expired(session):
                    perr = db.delete_encrypted_session(session.id)
                    if perr.isError():
                        err = DopUtils.create_dop_error(DopUtils.ERR_PL_SESSION_1)
                        err.perr = perr
                        payload = DopEventPayload(DopUtils.log_params('error', err.msg))
                        response_header = DopEventHeader(
                            event.header.session,
                            event.header.task,
                            DopEvent.LOG)
                        event = DopEvent(response_header, payload)
                        return [(event, err)]
                    perr = db.delete_session(session.id)
                    if perr.isError():
                        err = DopUtils.create_dop_error(DopUtils.ERR_PL_SESSION_2)
                        err.perr = perr
                        payload = DopEventPayload(DopUtils.log_params('error', err.msg))
                        response_header = DopEventHeader(
                            event.header.session,
                            event.header.task,
                            DopEvent.LOG)
                        event = DopEvent(response_header, payload)
                        return [(event, err)]

                    err = DopUtils.create_dop_error(DopUtils.ERR_SESSION_EXPIRED)
                    payload = DopEventPayload(DopUtils.log_params('error', err.msg))
                    response_header = DopEventHeader(
                        event.header.session,
                        event.header.task,
                        DopEvent.LOG)
                    event = DopEvent(response_header, payload)
                    return [(event, DopError())]
                
                return fn(*args, **kwargs)


            return decorator

        return wrapper

   

class BlockchainEvents:
    HAS_SUBSCRIBED = 'HasSubscribed'
    HAS_UNSUBSCRIBED = 'HasUnsubscribed'
    ALREADY_SUBSCRIBED = 'AlreadySubscribed'
    NOT_YET_SUBSCRIBED = 'NotYetSubscribed'
    NOT_YET_GRANTED = 'NotYetGranted'
    HAS_BEEN_GRANTED = "HasBeenGranted"
    HAS_BEEN_REVOKED = "HasBeenRevoked"
    ALREADY_GRANTED = "AlreadyGranted"
    HAS_DEPOSITED = "HasDeposited"
    HAS_BEEN_CHARGED = "HasBeenCharged"
    HAS_BEEN_CREDITED = "HasBeenCredited"
    HAS_BEEN_REFUNDED = "HasBeenRefunded"
    NO_CHARGE_APPLICABLE = "NoChargeApplicable"
    ILLEGAL_UNSUBSCRIBE = "IllegalUnsubscribe"
    ILLEGAL_GRANT = "IllegalGrant"
    KEY_CHANGED = "KeyChanged"


class TransactionEvents:
    REVOKE = 'revoke'
    DEPOSIT = 'deposit'
    GRANT = 'grant'
    UNSUBSCRIBE = 'unsubscribe'
    DEPLOY_CONTRACT = 'deploy_contract'
    SUBSCRIBE = 'subscribe'