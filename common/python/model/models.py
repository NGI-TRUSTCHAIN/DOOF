#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   author:     Georgiana
#   version:    1.1
#   date:       18/01/2024

 
from typing import Optional

from numpy import int32 


class TableName:
    USER = 'account'
    PRODUCT = 'product'

    TRANSACTION = 'blk_transaction'
    SESSION = 'session'
    TOKEN = 'token'                            
    PROPERTY = 'property'
    PROPERTY_PRODUCT = 'property_product'

    ENCRYPTED_SESSION = 'encrypted_session'
    PRODUCT_USAGE = 'product_usage'

    PRODUCT_SUBSCRIPTION = 'product_subscription'
    PURPOSE_OF_USAGE = 'purpose_of_usage'

    ACCOUNT_ROLE = "account_role"

 

class Model(object):
    def __init__(self,
                 **kargs):
        pass

    @classmethod
    def table_name(cls):
        raise NotImplementedError


class User(Model):
    def __init__(self,
                 *,
                 id: Optional[str] = None,
                 username: str,
                 name: str = '',
                 password: str,
                 blk_address: str,
                 blk_password: str,
                 is_admin: Optional[bool] = False, 
                 recipient: Optional[str] = None): 
        self.id = id
        self.password = password
        self.blk_password = blk_password
        self.blk_address = blk_address
        self.name = name
        self.username = username
        self.is_admin = is_admin
        self.recipient = recipient

    @classmethod
    def table_name(cls): return TableName.USER


class Product(Model):
    STATUS_CANCELLED = 0
    STATUS_CREATED = 1
    STATUS_PUBLISHED = 2

    def __init__(self,
                 *,
                 id: Optional[str] = None,
                 label: str,
                 tariff_price: Optional[int] = 0,
                 tariff_period: Optional[int] = 0,
                 data_origin_id: Optional[str] = None,
                 publisher: str, 
                 secret: str,
                 latitude: Optional[str] = None,
                 longitude: Optional[str] = None,
                 elevation: Optional[int] = None,
                 address: Optional[str] = None,
                 city: Optional[str] = None,
                 height: Optional[int] = 0,
                 status: Optional[int] = 0,
                 sensor_type: Optional[str] = None,
                 notes: Optional[str] = None,
                 blk_address: Optional[str] = None,
                 connstring_protocol: Optional[str] = None,
                 connstring_hostname: Optional[str] = None,
                 connstring_port: Optional[str] = None,
                 created_at: Optional[str] = None,      # ProductDetailSchema è DateDime; in db è timestamp; qua str
                 blk_specific: Optional[str] = None):
        self.tariff_period = tariff_period
        self.publisher = publisher
        self.data_origin_id = data_origin_id
        self.latitude = latitude
        self.longitude = longitude
        self.address = address
        self.city = city
        self.height = height
        self.elevation = elevation
        self.notes = notes
        self.sensor_type = sensor_type
        self.secret = secret
        self.status = status
        self.id = id
        self.blk_address = blk_address
        self.connstring_hostname = connstring_hostname
        self.connstring_port = connstring_port
        self.connstring_protocol = connstring_protocol
        self.created_at = created_at
        self.tariff_price = tariff_price
        self.label = label
        self.blk_specific = blk_specific

    @classmethod
    def table_name(cls): return TableName.PRODUCT


class Transaction(Model):

    def __init__(self,
                 *,
                 event_name: str,
                 client: str,
                 hash: str,
                 task: Optional[str] = None,
                 params: Optional[str] = None,
                 id: Optional[int] = None,
                 uuid: Optional[int] = None):
        self.client = client
        self.hash = hash
        self.task = task
        self.params = params
        self.id = id
        self.event_name = event_name
        self.uuid = uuid

    @classmethod
    def table_name(cls): return TableName.TRANSACTION


class Session(Model):
    def __init__(self, *,
                 client: str,
                 value: str,
                 token: Optional[str] = None,
                 status: Optional[int] = 0,
                 created_at: Optional[str] = None,
                 updated_at: Optional[str] = None,
                 last_updated: Optional[str] = None, 
                 id: Optional[int] = None):
        self.id = id
        self.value = value
        self.client = client
        self.token = token
        self.status = status
        self.created_at = created_at
        self.last_updated = last_updated
        self.updated_at = updated_at

    @classmethod
    def table_name(cls): return TableName.SESSION

class EncryptedSession(Model):
    def __init__(self, 
                *,
                id: Optional[int] = None, # for the creation of the object before having it in the db
                session_id: int, 
                cipher_name: str, 
                cipher_mode: str,
                cipher_keylength: int,
                key: str, #base64 
                encoding: Optional[str] = None, # ciphertext encoding
                integrity_fun: Optional[str] = None): # function used to verify integrity of message
        self.id = id
        self.session_id = session_id
        self.cipher_name = cipher_name
        self.cipher_mode = cipher_mode 
        self.cipher_keylength = cipher_keylength
        self.key = key
        self.encoding = encoding
        self.integrity_fun = integrity_fun

    @classmethod 
    def table_name(cls): return TableName.ENCRYPTED_SESSION


class ProductSubscription(Model): 
    def __init__(
            self, 
            *,
            id: str, 
            subscriber: str,
            subscriber_secret: Optional[str] = None,
            product: str,
            purpose_id: str,
            created_at: Optional[str] = None, 
            granted: Optional[int] = -1,
            pending: Optional[bool] = False,
            blk_address: Optional[str] = None
        ):
        self.id = id
        self.subscriber = subscriber
        self.subscriber_secret = subscriber_secret
        self.product = product 
        self.purpose_id = purpose_id
        self.created_at = created_at
        self.granted = granted 
        self.pending = pending
        self.blk_address = blk_address
        
    @classmethod
    def table_name(cls): return TableName.PRODUCT_SUBSCRIPTION

class PurposeOfUsage(Model):
    def __init__(self, 
                 *, 
                 id: str,
                 subscriber: str, 
                 label: Optional[str] = None,
                 url: Optional[str] = None):
        self.id = id 
        self.subscriber = subscriber
        self.label = label
        self.url = url

    @classmethod
    def table_name(cls): return TableName.PURPOSE_OF_USAGE



class PropertyProduct(Model):
    def __init__(self,
                 *,
                 id: Optional[int] = None,
                 property: int,
                 product: str):
        self.id = id
        self.product = product
        self.property = property

    @classmethod
    def table_name(cls): return TableName.PROPERTY_PRODUCT


class Property(Model):
    def __init__(self,
                 *,
                 id: Optional[int] = None,
                 property_value: str,
                 property_name: str):
        self.id = id
        self.property_value = property_value
        self.property_name = property_name

    @classmethod
    def table_name(cls): return TableName.PROPERTY

class ProductUsage(Model):

    def __init__(self, 
                *, 
                id: Optional[int] = None,
                product_id: str, 
                account_id: str,
                usage: int
                ):
        self.id = id
        self.product_id = product_id 
        self.account_id = account_id 
        self.usage = usage
        
        
    @classmethod
    def table_name(cls): return TableName.PRODUCT_USAGE
 


class AccountRole(Model):
    def __init__(self, 
                *, 
                id: Optional[int] = None, 
                account_id: str,
                role: str
                ):
        self.id = id
        self.account_id = account_id
        self.role = role

    
    @classmethod
    def table_name(cls):
        return TableName.ACCOUNT_ROLE
    
