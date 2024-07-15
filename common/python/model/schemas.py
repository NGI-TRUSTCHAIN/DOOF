# © Copyright Ecosteer 2024

#   author:     Georgiana
#   version:    1.0
#   date:       18/01/2024


from marshmallow import Schema, fields, post_load
from common.python.model.models import AccountRole


class UserSchema(Schema):
    id = fields.Str()
    username = fields.Str(required=True) 
    name = fields.Str(required=True)
    blk_address = fields.Str()
    blk_password = fields.Str()
    password = fields.Str()
    is_admin = fields.Boolean()
    recipient = fields.Str()


class TransactionSchema(Schema):
    id = fields.Int()
    hash = fields.Str(required=True)
    client = fields.Str(required=True)
    event_name = fields.Str(required=True)
    params = fields.Str()
    task = fields.Str()
    uuid = fields.Str()

 
class SessionSchema(Schema):
    id = fields.Int()
    client = fields.Str(required=True)
    value = fields.Str(required=True)
    status = fields.Int()
    token = fields.Str()
    created_at = fields.DateTime()  
    updated_at = fields.DateTime()  
    last_updated = fields.DateTime()

class EncryptedSessionSchema(Schema):
    id = fields.Int()
    session_id = fields.Int(required=True)
    cipher_name = fields.Str(required=True)
    cipher_mode = fields.Str(required=True)
    cipher_keylength = fields.Int(required=True) 
    key = fields.Str(required=True)
    encoding = fields.Str()
    integrity_fun = fields.Str()

class ProductCreateSchema(Schema): 
    id = fields.Str()
    sensor_type = fields.Str()
    notes = fields.Str()
    latitude = fields.Str()
    longitude = fields.Str()
    connstring_port = fields.Str()
    connstring_protocol = fields.Str()
    connstring_hostname = fields.Str()
    city = fields.Str()
    address = fields.Str()
    height = fields.Int()
    status = fields.Int()
    label = fields.Str()
    tariff_price = fields.Int()
    tariff_period = fields.Int()
    publisher = fields.Str()
    publisher_name = fields.Str(attribute="publisher_name")
    property_value = fields.Str(attribute="property_value")
    secret = fields.Str()
    blk_address = fields.Str()
    blk_specific = fields.Str()
    data_oridin_id = fields.Str()


class ProductSchema(Schema):
    id = fields.Str()
    sensor_type = fields.Str()
    notes = fields.Str()
    latitude = fields.Str()
    longitude = fields.Str()
    connstring_port = fields.Str()
    connstring_protocol = fields.Str()
    connstring_hostname = fields.Str()
    city = fields.Str()
    address = fields.Str()
    height = fields.Int()
    status = fields.Int()
    label = fields.Str(required=True)
    tariff_price = fields.Int()
    tariff_period = fields.Int()
    publisher = fields.Str(required=True) 
    publisher_name = fields.Str(required=True, attribute="publisher_name")
    property_value = fields.Str(attribute="property_value")
    secret = fields.Str()
    blk_address = fields.Str()
    blk_specific = fields.Str()
    data_origin_id = fields.Str()


class SubscriberSchema(Schema):
    subscriber_address = fields.Str()
    subscriber_username = fields.Str()
    subscriber_name = fields.Str()
    subscriber_id = fields.Str()
    created_at = fields.DateTime()
    balance = fields.Dict()



class PurposeOfUsageSchema(Schema):
    id = fields.Str(required=True)
    subscriber = fields.Str()
    label = fields.Str()
    url = fields.Str()

class ProductSubscriptionSchema(Schema):
    id = fields.Str(required=True)
    subscriber = fields.Str(required=True)
    subscriber_secret = fields.Str()
    product = fields.Str(required=True)
    purpose_id = fields.Str(required=True)  
    created_at = fields.DateTime()   
    granted = fields.Int()
    pending = fields.Boolean()
    blk_address = fields.Str()



class PropertyProductSchema(Schema):
    id = fields.Int()
    property = fields.Int(required=True)
    product = fields.Str(required=True)


class PropertySchema(Schema):
    id = fields.Int()
    property_name = fields.Str(required=True)
    property_value = fields.Str(required=True)

class ProductUsageSchema(Schema):
    id = fields.Int()
    product_id = fields.Str(required=True) 
    account_id = fields.Str(required=True) 
    usage = fields.Int(required=True) 

class AccountRoleSchema(Schema):
    id = fields.Int()
    account_id = fields.Str(required = True)
    role = fields.Str(required=True)

    @post_load 
    def create_account(self, data, **kwards):
        return AccountRole(**data)
