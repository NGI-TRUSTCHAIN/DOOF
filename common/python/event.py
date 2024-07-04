#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

"""
Minimalistic implementation of platform's events
Events are data set (usually imperatives) exchanged between
all the DOP components
"""


from abc import ABC, abstractmethod
import json

class AbstractHeader(ABC):
    """
    The AbstractHeader class contains information that is common to the 
    headers of two types of events - the DopEvent and the TransportEvent. 
    It is subsclassed by the concrete implementations DopEventHeader and 
    TransportEventHeader, which implement some of the properties defined here.
    AbstractHeader contains information regarding session.
    """
    def __init__(self, session="n/a"):
        self._session = session
        self._mle = None

    @property
    def session(self):
        """ 
        The session to which the event is sent
        """
        return self._session

    @property
    def mle(self):
        """ 
        The field 0/1, which indicates if the event is
        encapsulated via the Message Level Encryption protocol 
        or not
        """
        return self._mle

    # PROPERTIES FOR DopEventHeader
    @property 
    @abstractmethod 
    def task(self):
        """
        Task of event - for reactor pattern 
        """

    @property
    @abstractmethod 
    def event(self):
        """
        Event label
        """


    # PROPERTIES FOR TransportEventHeader 
    @property 
    @abstractmethod 
    def cipher_suite_name(self):
        """
        The cipher suite name with which the event was 
        encrypted.
        """

    @property 
    @abstractmethod 
    def integrity_fun(self):
        """
        The integrity function used to sign the event
        """

    @property 
    @abstractmethod 
    def digest(self):
        """
        The digest of the event, computed according to the 
        specified integrity function
        """

    @session.setter
    def session(self, session):
        self._session = session

    @mle.setter
    def mle(self, mle):
        self._mle = mle
    
    @task.setter 
    @abstractmethod
    def task(self, task):
        """
        """

    @event.setter 
    @abstractmethod 
    def event(self, event):
        """"""
    
    @cipher_suite_name.setter
    @abstractmethod 
    def cipher_suite_name(self, cipher_suite_name):
        """
        """
    
    @integrity_fun.setter 
    @abstractmethod 
    def integrity_fun(self, integrity_fun):
        """"""

    @digest.setter 
    @abstractmethod 
    def digest(self, digest):
        """"""

    # COMMON METHODS

    @abstractmethod 
    def to_dict(self):
        """
        Get a dictionary representing this header
        """

    @abstractmethod 
    def from_dict(self, event_dictionary: dict) -> bool:
        """
        Parse a dictionary to create a header
        """

    def __repr__(self):
        if self.mle is not None: 
            return f"{'session':{self._session}, 'mle':{self.mle}}" 
        return f"{'session':{self._session}}"


class DopEventHeader(AbstractHeader):
    def __init__(self, session: str = "n/a", task: str = "n/a", DopEvent: str = "n/a"):
        super().__init__(session)
        self._task = task 
        self._event = DopEvent


    @property  
    def task(self):
        return self._task

    @property
    def event(self):
        return self._event

    @property 
    def cipher_suite_name(self):
        return None

    @property 
    def integrity_fun(self):
        return None

    @property 
    def digest(self):
        return None

    
    @task.setter 
    def task(self, task):
        self._task = task

    @event.setter 
    def event(self, event):
        self._event = event
    
    @cipher_suite_name.setter
    def cipher_suite_name(self, cipher_suite_name):
        pass
    
    @integrity_fun.setter 
    def integrity_fun(self, integrity_fun):
        pass

    @digest.setter 
    def digest(self, digest):
        pass

    def to_dict(self):
        ev: dict = {}
        if self._session and self._session != 'n/a': 
            ev['session'] = self._session 
        
        ev['task'] = self._task
        ev['event']=  self._event
 
        if self.mle is not None:
            ev['mle'] = self.mle 

        return ev

    def from_dict(self, event_dictionary: dict):
        has_task = 'task' in event_dictionary 
        has_event = 'event' in event_dictionary

        self._session = event_dictionary.get('session', 'n/a')
        
        if has_task and has_event:
            self._task = event_dictionary['task']
            self._event = event_dictionary['event']
            if 'mle' in event_dictionary: 
                self._mle = event_dictionary['mle']
            return True
        return False

    def __repr__(self):
        return json.dumps(self.to_dict())


class TransportEventHeader(AbstractHeader): # MLE event header
    """
    Header for the MLE encapsulated event. The event header contains 
    information regarding session, cipher and integrity check selector.
    """
    def __init__(self, session: str="n/a", cipher_suite_name: str="n/a",
         integrity_fun: str="n/a", digest: str="n/a"):
        super().__init__(session)
        self._cipher_suite_name = cipher_suite_name 
        self._integrity_fun = integrity_fun 
        self._digest = digest 

    
    @property  
    def task(self):
        return None

    @property
    def event(self):
        return None

    @property 
    def cipher_suite_name(self):
        return self._cipher_suite_name

    @property 
    def integrity_fun(self):
        return self._integrity_fun

    @property 
    def digest(self):
        return self._digest

    @task.setter 
    def task(self, task):
        pass

    @event.setter 
    def event(self, event):
        pass
    
    @cipher_suite_name.setter
    def cipher_suite_name(self, cipher_suite_name):
        self._cipher_suite_name = cipher_suite_name
    
    @integrity_fun.setter 
    def integrity_fun(self, integrity_fun):
        self._integrity_fun = integrity_fun

    @digest.setter 
    def digest(self, digest):
        self._digest = digest

    def to_dict(self):
        ev: dict = {}
        if self._session and self._session != 'n/a': 
            ev['session'] = self._session 
        
        ev['cipher_suite_name'] = self._cipher_suite_name
        ev['integrity_fun'] = self._integrity_fun
        ev['digest'] = self._digest
        
        if self.mle is not None:
            ev['mle']=self.mle 

        return ev


    def from_dict(self, event_dictionary: dict):
        has_csn = 'cipher_suite_name' in event_dictionary 
        has_int_f = 'integrity_fun' in event_dictionary
        has_digest = 'digest' in event_dictionary
        
        self._session = event_dictionary.get('session','n/a')

        if has_csn and has_int_f and has_digest:
            self._session = event_dictionary['session']
            self._cipher_suite_name = event_dictionary['cipher_suite_name']
            self._integrity_fun = event_dictionary['integrity_fun']
            self._digest = event_dictionary['digest']
            if 'mle' in event_dictionary: 
                self._mle = event_dictionary['mle']
            return True
        return False
    
    
    def __repr__(self):
        return json.dumps(self.to_dict())

    


class DopEventPayload:
    def __init__(self, payload: dict = {}):
        self._payload = payload

    def to_dict(self) -> dict:
        return self._payload

    def from_dict(self, event_dictionary: dict) -> bool:
        has_payload = 'params' in event_dictionary
        if has_payload:
            self._payload = event_dictionary['params']
            return True 
        else:
            return False

    def __repr__(self):
        return json.dumps(self.to_dict())


class DopEvent:

    # front-end events
    CIPHER_SUITE_QUERY = 'cipher_suite_query'
    EVENT_SET = 'event_set'
    EVENTS_SET = 'events_set'

    CLIENT_READY = 'client_ready'

    LOG = 'log'
    CIPHER_SUITE = 'cipher_suite'
    SUBSCRIBER_CONFIG = 'subscriber_config'
    PUBLISHER_CONFIG = 'publisher_config'
    SUBSCRIPTION_STATUS = 'subscription_status' 
    
    MLE_NOTIFICATION = 'mle_start'
    START_SESSION_NOTIFICATION = 'start_session_status' #may not be received by the client 
    ERROR = 'error'
    SESSION_INFO = 'session_info'

    ENABLE_IDENTITY = "enable_identity"
    CIPHER_SUITE_SELECTION = "cipher_suite_selection"

    DOP_PRODUCTS_LIST = "dop_products_list"
    DOP_ROLE_ADD = "dop_role_add"
    DOP_ROLE_REMOVE = "dop_role_remove"
    DOP_SERVICE_ADD = "dop_service_add"
    DOP_SERVICE_LIST = "dop_service_list"
    DOP_PAY_SERVICE = "dop_pay_for_service"


    def __init__(self, header: AbstractHeader = None, payload: DopEventPayload = None):
        self._header = header
        self._payload = payload

    @property
    def header(self):
        return self._header

    @property
    def payload(self):
        return self._payload

    def to_dict(self) -> dict:
        pdict: dict = self.payload.to_dict()
        res = res = {**self._header.to_dict(), 'params': pdict}
        return res

    def from_dict(self, event_dictionary: dict) -> bool:
        self._header = DopEventHeader()
        self._payload = DopEventPayload()
        header_ok = self._header.from_dict(event_dictionary)
        payload_ok = self._payload.from_dict(event_dictionary)
        return header_ok and payload_ok

    def __repr__(self):
        return json.dumps(self.to_dict())