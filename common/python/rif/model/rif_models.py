#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   ver:    1.0
#   date:   20/05/2024
#   author: georgiana-bud

from typing import Optional

from common.python.model.models import TableName, Model


class RifTableName(TableName):
    RIF_ADVERTISEMENT = "rif_advertisement"
    RIF_ADVERTISEMENT_INTEREST = "rif_advertisement_interest"
    RIF_PRIVATE_MESSAGE = "rif_private_message"
    RIF_SUBSCRIPTION_NEWS = "rif_subscription_news"
    DOP_NOTIFICATION  = "rif_subscription_news"


class RifAdvertisement(Model):
    def __init__(self, 
                 *, 
                 id: Optional[str] = None, 
                 ads_lock: str, 
                 description: str, 
                 purpose_id: str, 
                 partner_id: str, 
                 recipient_ads_id: str,
                 created_at: Optional[str] = None
                 ):
        
        self.id = id
        self.ads_lock = ads_lock
        self.description = description
        self.purpose_id = purpose_id 
        self.partner_id = partner_id 
        self.created_at = created_at 
        self.recipient_ads_id = recipient_ads_id
    
    @classmethod 
    def table_name(cls):
        return RifTableName.RIF_ADVERTISEMENT
    
    
class RifAdvertisementInterest(Model):
    def __init__(self, 
                 *, 
                 id: Optional[str] = None, 
                 account_id: str, 
                 advertisement_id: str, 
                 accept: bool,
                 product_id: str, 
                 created_at: Optional[str] = None
                 ):
        
        self.id = id
        self.account_id = account_id
        self.advertisement_id = advertisement_id
        self.accept = accept
        self.product_id = product_id
        self.created_at = created_at

    
    @classmethod 
    def table_name(cls): 
        return RifTableName.RIF_ADVERTISEMENT_INTEREST
    
    
class RifPrivateMessage(Model):
    def __init__(self, 
                 *, 
                 id: Optional[str] = None, 
                 lock: str, 
                 subscription_id: str, 
                 message: str, 
                 send_to: str, 
                 created_at: Optional[str] = None 
                 ):
        self.id = id
        self.lock = lock
        self.subscription_id = subscription_id
        self.message = message
        self.send_to = send_to
        self.created_at = created_at

    
    @classmethod 
    def table_name(cls):
        return RifTableName.RIF_PRIVATE_MESSAGE
    
class RifSubscriptionNews(Model):
    def __init__(self, 
                 *, 
                 id: Optional[str] = None,  
                 subscription_id: Optional[str] = None, 
                 product_id: str, 
                 supplicant_id: str,
                 purpose_id: str,
                 action: str,
                 send_to: str, 
                 created_at: Optional[str] = None
                ):
        self.id = id
        self.subscription_id = subscription_id
        self.product_id = product_id 
        self.supplicant_id = supplicant_id 
        self.purpose_id = purpose_id 
        self.action = action
        self.send_to = send_to
        self.created_at = created_at

    
    @classmethod 
    def table_name(cls):
        return RifTableName.RIF_SUBSCRIPTION_NEWS

class DopNotification(Model):
    def __init__(self, 
                 *, 
                 id: Optional[str] = None,  
                 subscription_id: Optional[str] = None, 
                 content: str, 
                 send_to: str, 
                 created_at: Optional[str] = None
                ):
        self.id = id
        self.subscription_id = subscription_id
        self.content = content
        self.send_to = send_to
        self.created_at = created_at

    
    @classmethod 
    def table_name(cls):
        return RifTableName.DOP_NOTIFICATION