#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

dop_account_info = {
    "session":"",
    "task":"",
    "event":"dop_account_info",
    "params": {
        "auth_token":""
}}

dop_cipher_suite_selection = {
    "session":"",
    "task":"",
    "event":"dop_cipher_suite_selection",
    "params": {
        "auth_token":"",
        "cipher_suite":{},
        "cipher_key":""
    }
}

dop_client_ready = {
    "session":"",
    "task":"",
    "event":"dop_client_ready",
    "params": {
        "auth_token":""
    }
}

dop_enable_identity = {
    "session":"",
    "task":"",
    "event":"dop_enable_identity",
    "params":   {
        "auth_token" : "", 
        "subject": "",
        "screen_name" : "", 
        "recipient": ""
    }
}

dop_product_create = {
    "session":"8abbc354-7258-11e9-a923-1681be663d3e",
    "task": 1,
    "event":"dop_product_create",
    "params":  {
        "auth_token":"",
        "label": "",
        "price":0,
        "period":0, 
        "data_origin_id": ""
  }
}

dop_product_subscribe = {
    "session":"",
    "task": "",
    "event":"dop_product_subscribe",
    "params": {
         "auth_token":"",
         "product_id":"",
         "purpose_id":""
    }
}

dop_product_subscriptions = {
    "session":"",
    "task": "",
    "event":"dop_product_subscriptions",
    "params": {
        "auth_token": "",
        "product_id": "",
        "type":"sub|all"
    }
}


dop_product_unsubscribe = {
    "session":"",
    "task": "",
    "event":"dop_product_unsubscribe",
    "params": {
         "auth_token":"",
         "subscription_id":""
    }
}

dop_products_list = {
    "session":"",
    "task": "",
    "event":"dop_products_list",
    "params": {
        "auth_token": "",
        "type":"all|other|published|subscribed",
       	"filter": {}
}
}

dop_pub_configuration = {
    "session":"",
    "task": "2",
    "event": "dop_pub_configuration",
    "params": {
        "auth_token": "",
        "product_id": ""
    }
}
 

dop_purpose_create = {
    "session":"",
    "task":"",
    "event":"dop_purpose_create",
    "params":   {
        "auth_token": "",
        "label": "",
        "content": ""
}
}

dop_purpose_list = {
    "session":"",
    "task":"",
    "event":"dop_purpose_list",
    "params":   {
        "auth_token": ""
}
}

dop_sub_configuration = {
    "session":"",
    "task": "",
    "event":"dop_sub_configuration",
    "params": {
         "auth_token":"",
         "subscription_id":""
    }
}


dop_subscription_grant = {
    "session":"",
    "task": "",
    "event":"dop_subscription_grant",
    "params": {
         "auth_token":"",
         "subscription_id":""
    }
} 

dop_subscription_info = {
    "session":"",
    "task": "",
    "event":"dop_subscription_info",
    "params": {
         "auth_token":"",
         "subscription_id":""
    }
}

dop_subscription_revoke = {
    "session":"",
    "task": "",
    "event":"dop_subscription_revoke",
    "params": {
         "auth_token":"",
         "subscription_id":""
    }
}


dop_recipient_set= {
    "session":"",
    "task":"1",
    "event":"dop_recipient_set",
    "params":   {
        "auth_token": "",
        "subject": "",
        "recipient":""
    }
}