#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   ver:    1.3
#   date:   21/05/2024
#   author: georgiana


from typing import Tuple, Type, Union

from common.python.error import DopError
from common.python.rif.model.rif_models import RifTableName, RifAdvertisement, \
    RifAdvertisementInterest, RifPrivateMessage, RifSubscriptionNews

from common.python.rif.model.rif_schemas import RifAdvertisementSchema, \
    RifAdvertisementInterestSchema, RifPrivateMessageSchema, \
    RifSubscriptionNewsSchema

from provider.python.persistence.postgres.postgres_provider import  dbProviderPostgres
from provider.python.persistence.postgres.postgres_provider import *


class RIFdbProviderPostgres(dbProviderPostgres): 
    def __init__(self):
        super().__init__()

    def insert_rif_advertisement(self, rif_advert: RifAdvertisement) \
        -> Tuple[Union[int, str, None], DopError]:

        _id, err = self._insert_obj(rif_advert,  RifAdvertisementSchema)
        return _id, err
    
    def get_rif_advertisement(self, where: dict={}) \
        -> Tuple[Union[RifAdvertisement, list, None], DopError]:
        
        return self._select_obj(RifAdvertisement, where)
    


    def insert_rif_advert_interest(self, rif_advert_int: RifAdvertisementInterest) \
        -> Tuple[Union[int, str, None], DopError]:
        _id, err = self._insert_obj(rif_advert_int,  RifAdvertisementInterestSchema)
        return _id, err
    
    def get_rif_advert_interest(self, where: dict={}) \
        -> Tuple[Union[RifAdvertisementInterest, list, None], DopError]:
        
        return self._select_obj(RifAdvertisementInterest, where)
    
    
    
    def insert_rif_priv_mess(self, rif_priv_mess: RifPrivateMessage) \
        -> Tuple[Union[int, str, None], DopError]:
        _id, err = self._insert_obj(rif_priv_mess,  RifPrivateMessageSchema)
        return _id, err
    
 
    def get_rif_priv_mess(self, where: dict={}) \
        -> Tuple[Union[RifPrivateMessage, list, None], DopError]:
        return self._select_obj(RifPrivateMessage, where)
 
    def get_mess_for_user(self, user_id)\
        -> Tuple[Union[list, dict, None], DopError]:
        query = """
            SELECT id, subscription_id, 
                message, created_at

            FROM rif_private_message 
            """
        where = {'send_to': user_id}
        return self._sql_select(query, where)
    
    def get_mess_with_info_for_user(self, user_id)\
    -> Tuple[Union[list, dict, None], DopError]:
        # Left outer join ensures that if the product subscription does not  
        # exist anymore, the query will still return the info about the messages
        
        # purpose of usage URL # from subscription_id - purpose_id -> purpose
        # subscriber name # from subscription_id - subscriber; ?product label # from product_id of subscription 
        query = """                    
            SELECT 
                m.id, m.subscription_id, 
                m.message, m.created_at,
                ps.purpose_id, 
                CONVERT_FROM(DECODE(u.label, 'BASE64'), 'UTF-8') as purpose_label, 
                CONVERT_FROM(DECODE(u.url, 'BASE64'), 'UTF-8') as purpose_url,
                a.name as partner_name 
            FROM rif_private_message  as m
            
            LEFT OUTER JOIN product_subscription as ps 
                ON m.subscription_id = ps.id 

            LEFT OUTER JOIN purpose_of_usage as u 
                ON ps.purpose_id = u.id 

            LEFT OUTER JOIN account as a 
                ON ps.subscriber = a.id

            """
        where = {'m.send_to': user_id}
        return self._sql_select(query, where)

    def insert_rif_subscription_news(self, rif_sub_news: RifSubscriptionNews)\
        -> Tuple[Union[int, str, None], DopError]:
        _id, err = self._insert_obj(rif_sub_news,  RifSubscriptionNewsSchema)
        return _id, err

    def get_rif_subscription_news(self, where={}):
        return self._select_obj(RifSubscriptionNews, where)

    ### more complex ###
    def get_rif_sub_news_info(self, user_id ) \
        -> Tuple[list, DopError]:
        query = """
            SELECT n.id, n.subscription_id, 
                n.product_id, 
                n.supplicant_id, 
                n.purpose_id, 
                n.action, 
                n.created_at, 
                p.label as product_label, 
                a.name as supplicant_name, 
                CONVERT_FROM(DECODE(u.label, 'BASE64'), 'UTF-8') as purpose_label, 
                CONVERT_FROM(DECODE(u.url, 'BASE64'), 'UTF-8') as purpose_url
            FROM 
                rif_subscription_news as n 
            INNER JOIN product as p ON 
                n.product_id = p.id 
            INNER JOIN account as a ON 
                n.supplicant_id = a.id 
            INNER JOIN  purpose_of_usage as u ON
                n.purpose_id = u.id 
        """ 
        
        where = {
                #'n.product_id':'p.id', 
                #'n.supplicat_id':'a.id',
                #'n.purpose_id': 'u.id',
                'send_to': user_id}
        #values = {'p.id', 'a.id', 'u.purpose_id', user_id}
        
        return self._sql_select(query, where)


    
    def get_ads_for_user(self, user_id: str) \
        -> Tuple[Union[list, dict, None], DopError]:
        # NOTE in processor using this function, ensure that 
        # "created_at" (datetime) is serialized correctly
        query  = f"""
            SELECT  b.id as ads_id, b.description, b.purpose_id, 
            b.partner_id, b.created_at, a.name as company_name, 
            u.label as purpose_label, u.url as purpose_url
            FROM {RifAdvertisement.table_name()} as b, {User.table_name()} as a, 
            {PurposeOfUsage.table_name()} as u  
            WHERE b.partner_id = a.id 
            AND b.purpose_id = u.id            
            AND 
            b.id IN
            (
            SELECT distinct ads_id from 
            (SELECT b.id as ads_id, p.id as product_id 
            FROM {RifAdvertisement.table_name()} as b 
            CROSS JOIN {Product.table_name()} as p 
            WHERE p.publisher = ?

            except 

            SELECT  i.advertisement_id as ads_id, p.id as product_id
            FROM {Product.table_name()} as p,
            {RifAdvertisementInterest.table_name()} as i
            WHERE p.publisher = ?
            and p.id = i.product_id
            ))
        """
        # user_id = '061bca88-1cc9-11ef-88b8-01fdef5ce8c7'
        try:
          
            err, cur = self._execute_with_retry(query, (user_id , user_id,))
            if err.isError():
                return [], err
            rows = cur.fetchall()
            results = serialize(rows, cur)
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            return [], DopError(311, "An exception occurred while retrieving the advertisement.")
        
        try:
            if isinstance(results, list) and len(results) > 0:
                result = []
                for element in results:
                    self._decode_purpose_prop(element, 'purpose_label')
                    self._decode_purpose_prop(element, 'purpose_url')
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            return None, DopError(112, "An exception occurred while mapping extracted data to model.")


        return results, DopError()
    


    def get_actionable_products(self, user_id, ads_id) \
        -> Tuple[Union[list, dict, None], DopError]:
        """
        Return only the products for which the user can still express an 
        action for the indicated ad 
        """
        q2 =  f""" 
            SELECT p.id, p.label, 
            p.created_at,
            t.no_subscriptions
            FROM {Product.table_name()} as p 
            
            JOIN (SELECT 
                p.id as product_id, 
                count(ps.id) as no_subscriptions
                FROM {Product.table_name()} as p 
                LEFT JOIN {ProductSubscription.table_name()} as ps 
                on p.id = ps.product 
                GROUP BY p.id) t    
            
            ON p.id = t.product_id
                
            WHERE p.publisher = ?
            AND p.id 
            NOT IN 
                (SELECT i.product_id
                FROM {RifAdvertisementInterest.table_name()} as i
                WHERE   
                i.account_id = ?
                AND
                i.advertisement_id = ?)

        """
        results = []
        try:
          
            err, cur = self._execute_with_retry(q2, (user_id, user_id, ads_id))
            if err.isError():
                return results, err
            rows = cur.fetchall()
            results = serialize(rows, cur)
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            return results, DopError(311, "An exception occurred while retrieving actionable products for ad.")
        
        return results, DopError()
        
