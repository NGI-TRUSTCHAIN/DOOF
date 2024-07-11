# © Copyright Ecosteer 2024

import http.client
import json
import re
import ssl

from threading import Event, Thread

from provider.python.presentation.output.provider_pres_output import outputPresentationProvider
from common.python.error import DopError
from common.python.event import DopEvent
from common.python.utils import DopUtils

class https_provider(outputPresentationProvider):
    
    """
    configuration:
     'host=192.168.1.91;port=5000;WBL_API=/imperatives;timeout=60;ssl=True'
     'host=192.168.1.91;port=5000;WBL_API=/imperatives;timeout=60;ssl=False'
     'host=192.168.1.91;port=5000;WBL_API=/imperatives;timeout=60;ssl=_create_unverified_context()'
    """

    def __init__(self):
        super().__init__()
        self.config = {}
        
        self._connection = ""  # http(s)_client
        self._host = ""
        self._port = ""
        self._timeout = ""
        self._secure_connection = False
        self._imperatives_endpoint = ""
        self._ssl = "" 

        self._configured = False
        self._protocol = "HTTP1/1"

    def init(self, connstring: str) -> DopError:
        """Example connstring   
        - HTTP unsecure connection:
        'host=192.168.1.91;port=5000;WBL_API=imperatives;timeout=60;ssl=False'
        'h=192.168.1.91;p=5000;WBL_API=imperatives;tout=60;ssl=False;'
        - HTTPS secure connection: 
        'host=192.168.1.91;port=5000;WBL_API=imperatives;timeout=60;ssl=self_signed' or 'ssl=_create_unverified_context()' or 'ssl=True'
        'h=192.168.1.91;p=5000;WBL_API=imperatives;tout=60;ssl=self_signed' or 'ssl=_create_unverified_context()' or 'ssl=True'
        """
        tupleConfig = DopUtils.config_to_dict(connstring)
        if tupleConfig[0].isError():
            self._on_error(tupleConfig[0])
            return tupleConfig[0]

        self.config = tupleConfig[1]

        has_host: bool= ('host' or 'h') in self.config 
        has_port: bool = ('port' or 'p') in self.config
        if (has_host and has_port) == False:
            derr: DopError = DopError(1,'Configuration missing mandatory parameter(s).')
            derr.rip()
            self._on_error(derr)
            return derr
        
       
        a, self._host = DopUtils.config_get_string(self.config, ['host','h'], None)
        wfc, self._port = DopUtils.config_get_int(self.config,['port','p'], 0)
        wfc, self._imperatives_endpoint = DopUtils.config_get_string(self.config,['WBL_API'],"imperatives")
        wfc, self._timeout = DopUtils.config_get_int(self.config,['timeout','tout'], 20)

        ssl_vals = ['True', 'true', 'False', 'false', 'self_signed', '_create_unverified_context()']
        wfc, self._ssl = DopUtils.config_get_string(self.config,['ssl'], 'False') # if nothing was specified, assume HTTP
        if self._ssl in ssl_vals:
            self._ssl = self._ssl.casefold()
        else: 
            return DopError(2, 'Invalid option for ssl.')

        if self._timeout < 0:
            self._timeout = 20
            self._on_error(DopError(0,"invalid timeout, using default"))

        self._configured = True
        self._on_error(DopError(0,'provider configured'))
        return DopError()
 
    def open(self) -> DopError:
        #self._connection = http.client.HTTPConnection(self._host, self._port, self._timeout)
        self._on_error(DopError(0,'provider opened'))
        return DopError()

    def close(self) -> DopError:
        #self._connection.close()
        self._on_error(DopError(0,'provider closed'))
        return DopError()

    def write(self, msg: str, additional_info: dict = None) -> DopError:
        """HTTP is a synchronous request/reply protocol, so when writing a message 
        the reply should be processed straight away
    
        Differentiate OOB request from JSON event
        e.g. OOB:endpoint --> FUN
        - request endpoint is different for oob requests
        - a GET request can be sent 
        OOB:%endpoint% 
        -> GET %endpoint%
        """
       
        # HTTPS SECURE CONNECTION
        # NOTE HTTPSConnection is a HTTPConnection (same APIs)
        if self._ssl == "self_signed" or self._ssl == '_create_unverified_context()':
            # testing phase, self signed cert
            self._connection = http.client.HTTPSConnection(self._host, self._port, timeout = self._timeout, context = ssl._create_unverified_context())
    
        elif self._ssl == "true": 
            self._connection = http.client.HTTPSConnection(self._host, self._port, timeout = self._timeout)
        elif self._ssl == "false": 
            # HTTP CONNECTION
            self._connection = http.client.HTTPConnection(self._host, self._port, timeout = self._timeout)

        if msg.startswith("@JSON;"):   
            # this is the routable request that needs to be forwarded to the worker
            headers = {'Content-Type': 'application/json'}
            if additional_info is not None and 'Authorization' in additional_info: 
                headers.update(additional_info)


            pref_len = len("@JSON;")
            if len(msg) > pref_len: 
                msg = msg[pref_len:] # substring after the prefix
                endpoint = self._imperatives_endpoint
                self._connection.request("POST", endpoint, msg, headers)
            else:
                return DopError(1, "Error in publishing your imperative: please insert the event to be sent.")
        elif msg.startswith("@FUN;"):
            pref_len = len("@FUN;")
            if len(msg) > pref_len:
                endpoint = msg[pref_len:]
                print(f"GET:/{endpoint}")
                self._connection.request("GET", f"{endpoint}")
            else: 
                self._connection.request("GET", "/") # request the index page
        else:
            return DopError(2, "Error in publishing your imperative: empty message.")
        

        # receive input
        response =""
        try:
            response = self._connection.getresponse()
            #print(f"Status: {response.status} and reason: {response.reason}")
        except ConnectionError:
            return DopError(102, "HTTP Connection error")

        #if not bool(re.match("2[0-9][0-9]", str(response.status))):
        #    self._on_error(DopError(response.status, f"{response.reason} {response.read()}"))

        
        #print(f"{response.status} {response.reason}")
        #print(content)
        response_data = {
            'response_status': response.status,
            'response_reason': response.reason,
            'response_headers': response.getheaders(),
            'response_content': response.read().decode("utf-8")
        }
        # on_data has topic and message - here we don't have a topic but we can consider HTTP REPLY as a topic
        self._on_data(f"HTTP REPLY for {endpoint}", json.dumps(response_data))
        self._connection.close()
        return DopError()


    
    def write_to_endpoint(self, msg: str, endpoint: str, additional_info: dict = None) -> DopError:
        """HTTP is a synchronous request/reply protocol, so when writing a message 
        the reply should be processed straight away
      
        Differentiate OOB request from JSON event
        e.g. OOB:endpoint --> FUN
        - request endpoint is different for oob requests
        - a GET request can be sent 
        OOB:%endpoint% 
        -> GET %endpoint%
        """
       
        # HTTPS SECURE CONNECTION
        # NOTE HTTPSConnection is a HTTPConnection (same APIs)
        if self._ssl == "self_signed" or self._ssl == '_create_unverified_context()':
            # testing phase, self signed cert
            self._connection = http.client.HTTPSConnection(self._host, self._port, timeout = self._timeout, context = ssl._create_unverified_context())
    
        elif self._ssl == "true": 
            self._connection = http.client.HTTPSConnection(self._host, self._port, timeout = self._timeout)
        elif self._ssl == "false": 
        # HTTP CONNECTION
            self._connection = http.client.HTTPConnection(self._host, self._port, timeout = self._timeout)

        if msg.startswith("@JSON;"):   
            # this is the routable request that needs to be forwarded to the worker
            headers = {'Content-Type': 'application/json'}
            
            if additional_info is not None and 'Authorization' in additional_info: 
                headers.update(additional_info)

            pref_len = len("@JSON;")
            if len(msg) > pref_len: 
                msg = msg[pref_len:] # substring after the prefix
                self._connection.request("POST", f"{endpoint}", msg, headers)
            else:
                return DopError(1, "Error in publishing your imperative: please insert the event to be sent.")
        elif msg.startswith("@FUN;"):
            pref_len = len("@FUN;")
            if len(msg) > pref_len:
                endpoint = msg[pref_len:]
                print(f"GET:/{endpoint}")
                self._connection.request("GET", f"/{endpoint}")
            else: 
                self._connection.request("GET", "/") # request the index page
        else:
            return DopError(2, "Error in publishing your imperative: empty message.")
        

        # receive input
        response =""
        try:
            response = self._connection.getresponse()
            #print(f"Status: {response.status} and reason: {response.reason}")
        except ConnectionError:
            return DopError(102, "HTTP Connection error")

        #if not bool(re.match("2[0-9][0-9]", str(response.status))):
        #    self._on_error(DopError(response.status, f"{response.reason} {response.read()}"))

        
        #print(f"{response.status} {response.reason}")
        #print(content)
        # TODO: search for the authorization header in the reponse.headers and return it to upper layer
        response_data = {
            'response_status': response.status,
            'response_reason': response.reason,
            'response_headers': response.getheaders(),
            'response_content': response.read().decode("utf-8")
        }
        # on_data has topic and message - here we don't have a topic but we can consider HTTP REPLY as a topic
        self._on_data(f"HTTP REPLY for {endpoint}", json.dumps(response_data))
        self._connection.close()
        return DopError()


    def writeEvent(self, msg: DopEvent, additional_info: dict = None) -> DopError:
        """HTTP is a synchronous request/reply protocol, so when writing a message 
        the reply should be processed straight away.
        The 'writeEvent' method works as the write of messages prepended by '@JSON;' 
        """
        # HTTPS SECURE CONNECTION
        # NOTE HTTPSConnection is a HTTPConnection (same APIs)
        if self._ssl == "self_signed" or self._ssl == '_create_unverified_context()':
            # testing phase, self signed cert
            self._connection = http.client.HTTPSConnection(self._host, self._port, timeout = self._timeout, context = ssl._create_unverified_context())
    
        elif self._ssl == "true": 
            self._connection = http.client.HTTPSConnection(self._host, self._port, timeout = self._timeout)
        elif self._ssl == "false": 
        # HTTP CONNECTION
            self._connection = http.client.HTTPConnection(self._host, self._port, timeout = self._timeout)
        

        headers = {'Content-Type': 'application/json'}
        if additional_info is not None and 'Authorization' in additional_info: 
                headers.update(additional_info)

        self._connection.request("POST", self._imperatives_endpoint, json.dumps(msg.to_dict()), headers)
        

        # receive input
        response =""
        try:
            response = self._connection.getresponse()
            #print(f"Status: {response.status} and reason: {response.reason}")
        except ConnectionError:
            return DopError(102, "HTTP Connection error")

        if not bool(re.match("2[0-9][0-9]", str(response.status))):
            self._on_error(DopError(response.status, f"{response.reason} {response.read()}"))

        response_data = {
            'response_status': response.status,
            'response_reason': response.reason,
            'response_headers': response.getheaders(),
            'response_content': response.read().decode("utf-8")
        }
        # on_data has topic and message - here we don't have a topic but we can consider HTTP REPLY as a topic
        self._on_data("HTTP REPLY", json.dumps(response_data))
        self._connection.close()
        
        return DopError()