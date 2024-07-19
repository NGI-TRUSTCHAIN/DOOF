#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   ver:    1.0
#   date:   14/06/2024
#   author: georgiana


rif_advertisement_create = {
    "session":"",
    "task":"",
    "event":"rif_advertisement_create",
    "params":  {
        "auth_token": "",
        "secret": "",
        "description": "",
        "purpose_id": "",
        "recipient_ads_id": ""
}
}


 
rif_advertisement_interest = {
    "session":"",
    "task":"",
    "event":"rif_advertisement_interest",
    "params":  {
        "auth_token": "",
        "accept": "",
        "ads_id": "",
        "purpose_id": "",
        "product_id": ""
}
}


rif_advertisement_list = {
    "session":"",
    "task":"",
    "event":"rif_advertisement_list",
    "params":  {
        "auth_token": "",
        "filter": "other"
}
}

rif_actionable_products = {
    "session":"",
    "task": "",
    "event":"rif_actionable_products",
    "params": {
	    "auth_token": "",
 	    "ads_id": "" 
}
}


rif_private_message_send = {
    "session":"",
    "task": "",
    "event":"rif_private_message_send",
    "params": {
	    "auth_token": "",
 	    "secret": "",
        "subscription_id": "",
        "message": "" 
}
}

rif_private_message_list = {
    "session":"",
    "task": "",
    "event":"rif_private_message_list",
    "params": {
	    "auth_token": ""
}
}


rif_news_list = {
    "session":"",
    "task": "",
    "event":"rif_news_list",
    "params": {
	    "auth_token": ""
}
}

dex_change_password = {
    "session":"",
    "task": "",
    "event":"dex_change_password",
    "params": {
	    "auth_token": "",
        "old_password": "",
        "new_password" :""
}
}

dex_change_screen = {
    "session":"",
    "task": "",
    "event":"dex_change_screen",
    "params": {
	    "auth_token": "",
        "new_screen_name":""
}
}