#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

# author:       georgiana
# date:         03/07/2024
# version:      1.0



import json
from typing import Tuple, List

import string
import random

from provider.python.processor.provider_processor import ProcessorProvider 
from common.python.error import DopError
from common.python.event import DopEvent, DopEventHeader, DopEventPayload

from common.python.model.models import  User, Product, Transaction
from common.python.model.schemas import ProductSchema

from common.python.new_processor_env import ProcessorEnvs
from common.python.utils import DopUtils, TransactionEvents as te


class DopProductCreateProcessor(ProcessorProvider):


    def __init__(self):
        super().__init__() 
        self._INT = 31
        self._BIGINT = 63   # 2**63-1 : 9223372036854775807 
        self._config = ""
        self._event_type = "dop_product_create"
        self._EXPONENT = self._INT           #integer values (positive and negative) 

    def init(self, config: str) -> DopError:
        self._config = config
        return DopError()

    def open(self) -> DopError:
        return DopError()

    def close(self) -> DopError:
        return DopError()


    def handle_event(self, event: DopEvent, envs: ProcessorEnvs) \
            -> DopError:
        
        """
        This events triggers the creation of a product.
        The emitter of this event must be authenticated
        and thus the property auth_troken has to be valid.

        event:{
            "session":"8abbc354-7258-11e9-a923-1681be663d3e",
            "task":"1",
            "event":"dop_product_create",
            "params":   {
                            "auth_token":"888ghj=89l;#",
                            "label":"GrandSens",
                            "price": 10,
                            "period": 5
                            }
                        }
        }

        """

        if self._event_type == event.header.event: 
            return self._handle_dop_product_create(event, envs)
        return DopError() 
    

    def _handle_dop_product_create(self, event, envs: ProcessorEnvs) -> DopError:

        blk = envs.blk_provider
        db = envs.db_provider
        payload = event.payload.to_dict()
        header = event.header
        phase = 0
        
        if 'label' not in payload:
            envs.events.push(header.event, 
                            DopEvent(header, DopEventPayload({
                                    "err" : DopUtils.ERR_MISS_LABEL['id'],
                                    "phase" : phase
                                })
                        ))
            return DopError()

        # get authenticated user from stack 
        try:
            user = envs.data.get(User.__name__)[0]
        except:
            #perr =  DopError(999, "missing data from pipeline data stack")
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_USER_NOT_FOUND)
            #err.perr = perr 
            return err

     

        label = payload.get('label')
        price = payload.get("price", 0)
        period = payload.get("period", 0)
        origin_id = payload.get("data_origin_id", "")
        
        # Range check
        min = -(2**self._EXPONENT-1) 
        max = 2**self._EXPONENT-1
        if (price < min or price > max) or \
            (period < min or period > max):
            envs.events.push(header.event, DopEvent(header, DopEventPayload({
                "err": DopUtils.ERR_PRODUCT_RANGE['id'],
                "phase": phase,
                "label" : label, 
                "price": price, 
                "period": period
            })))
            return DopError()


        # Generate the product id
        uuid_str = str(DopUtils.create_uuid())
        
        perr, blk_address = blk.marketplaceAddress(uuid_str)
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_IP_DEPLOY) # cannot get marketplace address of product
            err.perr = perr
            return err
        
        obj = {
            "id": uuid_str,
            "publisher": user.id,
            "secret": "secret",
            "label": label, 
            "blk_address": blk_address,
            "tariff_price": price,
            "tariff_period": period,
            "sensor_type": "static",
            "status": 2,
            "data_origin_id": origin_id
            }


        publisher_address = user.blk_address 
        if not publisher_address:
            err = DopUtils.create_dop_error(DopUtils.ERR_USER_ADDRESS)
            envs.events.push(header.event,DopEvent(header, DopEventPayload({
                "err": DopUtils.ERR_USER_ADDRESS['id'],
                "phase": phase,
                "label" : label, 
                "price": price, 
                "period": period
            })) )

            return DopError() 

        
        # instead of returning the smart contract address, return the tid 

        perr, tx_hash = blk.productCreate(
            uuid_str, 
            publisher_address, 
            publisher_address,
            user.blk_password, 
            price, 
            period
        )
        #err hex 64 - decimal 100 - member does not exist?

        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_IP_DEPLOY)
            err.perr = perr
            return err
        
        # Save the tx_hash(transaction id) in the database, together with 
        # any other information needed for the completion of the request 
        

        product = Product(**obj)
        data = ProductSchema().dumps(product)
        
        data_js = json.loads(data)
        data_js["original_session"] = event.header.session

        transaction = Transaction(
            hash=tx_hash, 
            event_name=self._event_type,
            client=user.id, 
            task = header.task,
            params=json.dumps(data_js)
        )

        perr = db.create_transaction(transaction)
        if perr.isError():
            err = DopUtils.create_dop_error(DopUtils.ERR_PL_TRANSACT_SAVE)
            err.perr = perr
            return err

        
        envs.events.push(header.event, DopEvent(header, DopEventPayload({
            "err":0,
            "product_id" : uuid_str,
            "phase" : phase,
            "label" : label, 
            "price": price, 
            "period": period,
            "data_origin_id": origin_id
        })))
        return DopError()



