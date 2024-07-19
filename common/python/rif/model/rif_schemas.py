#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   ver:    1.0
#   date:   20/05/2024
#   author: georgiana-bud

from marshmallow import Schema, fields, post_load 
from common.python.rif.model.rif_models import *

class RifAdvertisementSchema(Schema):
    id = fields.Str()
    ads_lock = fields.Str(required = True)
    description = fields.Str(required = True)
    purpose_id = fields.Str(required = True)
    partner_id = fields.Str(required = True) 
    recipient_ads_id = fields.Str(required = True)
    created_at = fields.DateTime()  

    @post_load
    def create_rif_advertisement(self, data, **kwards):
        return RifAdvertisement(**data)
    

class RifAdvertisementInterestSchema(Schema):
    id = fields.Str()
    account_id = fields.Str(required = True)
    advertisement_id = fields.Str(required = True)
    accept = fields.Boolean(required = True)
    product_id = fields.Str(required = True)
    created_at = fields.DateTime()  

    @post_load
    def create_rif_advertisement_interest(self, data, **kwards):
        return RifAdvertisementInterest(**data)


class RifPrivateMessageSchema(Schema):
    id = fields.Str() 
    lock = fields.Str(required=True) 
    subscription_id = fields.Str(required=True)
    message = fields.Str(required=True)
    send_to = fields.Str(required = True)
    created_at = fields.DateTime()  

    @post_load
    def create_rif_private_message(self, data, **kwards):
        return RifPrivateMessage(**data)

class RifSubscriptionNewsSchema(Schema):
    id = fields.Str()
    subscription_id = fields.Str(required = True)
    product_id = fields.Str(required = True)
    supplicant_id = fields.Str(required = True)
    purpose_id = fields.Str(required = True)
    action = fields.Int(required = True) 
    send_to = fields.Str(required = True)
    created_at = fields.DateTime()

class DopNotificationSchema(Schema):
    id = fields.Str()
    subscription_id = fields.Str()
    content = fields.Str(required=True) 
    send_to = fields.Str(required=True)
    created_at = fields.DateTime()  

    @post_load
    def create_dop_notification(self, data, **kwards):
        return DopNotification(**data)