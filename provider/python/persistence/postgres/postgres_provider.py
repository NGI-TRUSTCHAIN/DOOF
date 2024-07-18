#   SPDX-License-Identifier: Apache-2.0
# © Copyright 2024 Ecosteer

#   ver:    1.0
#   date:   30/05/2024
#   author: georgiana


import copy
import inspect
from functools import wraps
from inspect import currentframe, getframeinfo

import pyodbc
from typing import Tuple, Type, Union
 

from common.python.error import DopError
from provider.python.persistence.provider_persistence import providerPersistence

from common.python.model.models import User, Transaction, Product, Session, \
    EncryptedSession, Model, Property, PropertyProduct, \
    TableName, AccountRole


from common.python.model.schemas import EncryptedSessionSchema, TransactionSchema, \
    ProductSchema, UserSchema, \
    SessionSchema, PropertySchema, \
    PropertyProductSchema, AccountRoleSchema


from common.python.model.models import ProductUsage
from common.python.model.schemas import ProductUsageSchema

from common.python.model.models import PurposeOfUsage, ProductSubscription

from common.python.model.schemas import PurposeOfUsageSchema, ProductSubscriptionSchema


from common.python.utils import DopUtils


import time
import traceback
import sys


def serialize(resource, cursor):
    response = {}
    if isinstance(resource, list):
        response = []
        for row in resource:
            response.append(serialize(row, cursor))
    else:
        if resource:
            for idx, value in enumerate(resource):
                response[cursor.description[idx][0]] = value
    return response


class dbProviderPostgres(providerPersistence):

    LIMIT = 50

    def __init__(self):
        
        self._config = None
        self._url = None
        self._connection = None

        self._recovery_delay_s = 5    #   delay in seconds that have to be waited for before recovery
        self._recovery_max = 10       #   maximum number of attempts to recover
        self._timeout = 5       # timeout in seconds for the connection setup and for the queries

        super().__init__()

    def init(self, config: str) -> DopError:
        """Parse the configuration string: 
        "driver=PostgreSQL Unicode;servername=localhost;port=5432;database=ecosteer;uid=ecosteer;pwd=ecosteer"
        """
        self._config = config 
        return DopError()
    
    def open(self) -> DopError:
        if self._connection != None:
            #   connected already (likely still ok)
            return DopError(0)
        sys.stdout.flush()
        max_retry = self._recovery_max
        while max_retry > 0:
            try:
                self._connection = pyodbc.connect(self._config, timeout = self._timeout)
                self._connection.autocommit = False
                self._connection.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
                self._connection.setencoding(encoding='utf-8')
            except Exception as e:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
                sys.stderr.flush()
                if isinstance(e, pyodbc.OperationalError) or isinstance(e, pyodbc.Error):
                    if self._recoverable(e):
                        max_retry -= 1
                        print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                            f"{getframeinfo(currentframe()).lineno} | Recovering from last error. Retries left: {max_retry}.\n", file = sys.stderr)
                        self._recovery_delay()
                        continue
                return DopError(99, "Non recoverable error while opening postgres persistence provider.") 
                
            return DopError(0, "Postgres provider opened.")
        return DopError(120, "Could not connect to the database: max number of attempts exceeded") 


    def _recoverable(self, e:Exception) -> bool:
        exception_type: str = type(e).__name__
        #print("REC TYPE: " + exception_type)
        #print("REC CODE: " + e.args[0])
        if exception_type == "OperationalError":
            if e.args[0]=='08001' or e.args[0] == '08S01':             
                return True
        if exception_type == "Error":
            if e.args[0]=='57P01' or e.args[0] == 'HY000':
                return True  
        return False

    def _recovery_delay(self):
        time.sleep(self._recovery_delay_s)

    def close(self) -> DopError:
        if self._connection:
            self._connection.close()
            self._connection = None 
        return DopError(0, "Postgres provider closed.")

    def _reconnect(self) -> DopError:
        #   any reconnection is not responsibility of the provider client but
        #   it is responsibility of the provider itself
        return DopError()
    
    def begin_transaction(self) -> DopError:
        return DopError()
        
    
    def rollback(self) -> DopError:
        max_retry = self._recovery_max
        while max_retry > 0: # check exit condition: if exception is not pyodbc.Error what happens
                
            err = self.open()
            if err.isError():
                return err

            try: 
                self._connection.rollback()
            except Exception as e:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                        f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)

                sys.stderr.flush()

                if isinstance(e, pyodbc.Error):
                    if self._recoverable(e):
                        max_retry -= 1
                        print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                            f"{getframeinfo(currentframe()).lineno} | Recovering from last error. Retries left: {max_retry}.\n", file = sys.stderr)
                        self.close()
                        self._recovery_delay()
                        continue

                    return DopError(100, "Non recoverable error during rollback.")
            return DopError() # rollback was successful
        return DopError(101, "Error during rollback.")
    
    def commit(self) -> DopError: 
        
        max_retry = self._recovery_max
        while max_retry > 0: # check exit condition
                
            err = self.open()
            if err.isError():
                return err

            try:
                self._connection.commit()
            except Exception as e:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                        f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)

                sys.stderr.flush()

                if isinstance(e, pyodbc.Error): # probably this can be eliminated 
                    if self._recoverable(e):
                        max_retry -= 1
                        print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                            f"{getframeinfo(currentframe()).lineno} | Recovering from last error. Retries left: {max_retry}.\n", file = sys.stderr)
                        self.close()
                        self._recovery_delay()
                        continue
                    return DopError(102, "Non recoverable error during commit.")

            return DopError()     
        return DopError(103, "Error during commit.")
        

    def create_user(self, user: User) -> DopError:
        # NOTE To improve security it is better to delegate the password hashing
        # to the db provider.
        # In this way we are sure that a processor will not save the password
        #  as plain text.

        # TODO add utils of worker

        user.password = DopUtils.hash_string(user.password) 
        _id, err = self._insert_obj(user, UserSchema)
        return err
    
    def update_user(self, user: User) -> DopError:
        return self._sql_update(
            User.table_name(),
            _where = {'id': user.id},
            update=UserSchema().dump(user))


    
    def create_transaction(self, transaction: Transaction) -> DopError:
        _id, err = self._insert_obj(transaction, TransactionSchema)
        return err

    
    def create_product(self, product: Product, uuid: str) -> Tuple[int,DopError]: 
        product.id = uuid
        _id, err = self._insert_obj(product, ProductSchema)

        if err.isError(): 
            return 0, err 

        product_usage = ProductUsage(
            product_id = uuid, 
            account_id = product.publisher,
            usage = 1 # account is publisher
        )
        err = self.create_product_usage(product_usage)

        return _id, err

   
    def create_product_usage(self, product_usage: ProductUsage) -> DopError:
        _id, err = self._insert_obj(product_usage, ProductUsageSchema)
        return err
    
    def update_or_create_session(self, session: Session) -> DopError: 
        session_obj, err = self.get_session({'client': session.client})

        if not session_obj:
            _id, err = self._insert_obj(session, SessionSchema)
            return err
    
        elif isinstance(session_obj, list):
            session_obj = session_obj[0]
            
        elif err.isError():

            return err

        # For multisession functionality:
        # only insert_obj here; do not update old sessions; 
        return self.update_session(session_obj.id, **SessionSchema().dump(session))
        



    def create_session(self, session: Session) -> DopError:
        _id, err = self._insert_obj(session, SessionSchema)
        return err


     
    def user_verify(self, username, password) -> DopError: 
        """
        Check username and password
        :param username:
        :param password:
        :return:
        """
        user, err = self.get_user_from_username(username)
        if err.isError():
            return err
        if not DopUtils.verify_hash(user.password, password):
            return DopError(301, "Wrong username or password.")
        return DopError()

    
    def isOwner(self, publisher_id, product_address: str) \
           -> Tuple[bool, DopError]: 
        query = """SELECT * 
                   FROM product
                   WHERE publisher=?
                   AND blk_address=?;
        """
        try:
        
            err, cursor = self._execute_with_retry(query, (publisher_id, product_address,))
            result = cursor.fetchone()

            result = serialize(result, cursor)
            if not result:
                return False, DopError(0,"No product was found.")
        except Exception as e:
            if e.args and len(e.args) > 0:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                        f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)

                sys.stderr.flush()
                return False, DopError(302, "An exception occurred while retrieving the products of the specified user.")
            return False, DopError(302,"An exception occurred while retrieving the products of the specified user.")

        return True, DopError()

    def get_session_and_mle(self, curr_client_session) -> Tuple[list, DopError]:
        query_session = f"""
                    SELECT  s.client, 
                    s.value,
                    e.cipher_name, 
                    e.cipher_mode, 
                    e.cipher_keylength,
                    e.key, 
                    e.integrity_fun, 
                    e.encoding
            FROM    {TableName.SESSION} as s 
            INNER JOIN {TableName.ENCRYPTED_SESSION} as e
            ON    s.id = e.session_id
            """
        where = {'s.value' : curr_client_session}
        return self._sql_select(query_session, where)


    def get_client_sessions_and_mle(self, curr_client_session)\
            -> Tuple[list, DopError]:
        query_sessions = """
            SELECT  s.client, 
                    s.value,
                    e.cipher_name, 
                    e.cipher_mode, 
                    e.cipher_keylength,
                    e.key, 
                    e.integrity_fun, 
                    e.encoding
            FROM    {table_session} as s, {table_enc_session} as e
            WHERE   s.id = e.session_id
            AND     s.client in 
            (
                SELECT  client 
                FROM    {table_session}
                WHERE   value = ?
            )
            """.format( 
                table_session=TableName.SESSION,
                table_enc_session=TableName.ENCRYPTED_SESSION
            )

        results =  []
        
        try:
          
            err, cur = self._execute_with_retry(query_sessions, (curr_client_session ,))
            if err.isError():
                return results, err
            rows = cur.fetchall()
            results = serialize(rows, cur)
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            return results, DopError(311, "An exception occurred while retrieving the user's open sessions.")
        return results, DopError()

    def get_transaction(self, where: dict) \
            -> Tuple[Union[Transaction, list, None], DopError]: 
        return self._select_obj(Transaction, where)

    def get_product_usage(self, where: dict = None) \
                            -> Tuple[Union[list, ProductUsage, None], DopError]:
        
        return self._select_obj(ProductUsage, where)
 
     
    def get_user(self, where: dict = None) \
            -> Tuple[Union[User, list, None], DopError]: 
        """
        Select from the User table

        :param where:
        """
        return self._select_obj(User, where)

      
    def get_product_reference(self, product_id) \
            -> Tuple[dict, DopError]: 
        """
            Retrieve product blk address and publisher blk address by product id (marketplace id)
        """

        query_product = """
        SELECT      {table_product}.blk_address as product_blk_address,
                    {table_product}.blk_specific as product_blk_specific,
                    {table_user}.blk_address as publisher_blk_address
        FROM        {table_product},{table_user} 
        WHERE       {table_product}.id='{pid}'
        AND         {table_user}.id={table_product}.publisher
        """.format(
            table_product=TableName.PRODUCT,
            table_user=TableName.USER,
            pid=product_id
        )


        products, err = self._sql_select(query_product)
        if err.isError():
            # was err 304
            return {}, DopError(304,"The requested product reference could not be retrieved. Please check if the product exists.")
        
        if len(products) == 0:
            return {}, DopError(0,"The requested product reference could not be retrieved. Please check if the product exists.")
        
        product = products[0]
        return product, err


        

    def get_product(self, where: dict = None) \
            -> Tuple[Union[Product, list, None], DopError]:  # actually Product --> dict
        """
        Get all the products

        :param where:
        """
        """
        NOTE: the query of property was deleted: 
            SELECT pr.property_value as property_value
        ... 
            LEFT JOIN {table_property_product} as pp ON pp.product = p.id
            LEFT JOIN {table_property} as pr ON pp.property = pr.id
        """
        query = """
            SELECT p.id,
                   p.blk_address,
                   p.blk_specific,
                   p.label, 
                   p.latitude, 
                   p.longitude, 
                   p.address, 
                   p.city, 
                   p.publisher,
                   a.name as publisher_name,
                   a.username as publisher_username
            FROM {table_product} as p 
            JOIN {table_user} as a ON p.publisher = a.id
            
        """.format(
            table_product=TableName.PRODUCT,
            table_user=TableName.USER
            #,
            #table_property_product=TableName.PROPERTY_PRODUCT,
            #table_property=TableName.PROPERTY
        )
        if where.get('subscriber'):
            query += ' LEFT JOIN {table_products_subscribers} as ps ON ps.product = p.id'.format(
                table_products_subscribers=TableName.PRODUCTS_SUBSCRIBERS
            )
            where['ps.subscriber'] = where.pop('subscriber')
        _filter = copy.deepcopy(where)
        product_columns = inspect.signature(Product).parameters
        for key, value in where.items():
            if key in product_columns:
                new_key = 'p.' + key
                _filter[new_key] = where[key]
                _filter.pop(key)
        #_filter['pr.property_name'] = 'type'
        # TODO status to be decided by client
        _filter['status'] = 2

        return self._sql_select(query, _filter)

    def get_products_limits(self, start, limit)\
        -> Tuple[Union[dict, list, None], DopError]:
        query = f"""
            SELECT distinct 
                    p.id, 
                    p.label, 
                    p.created_at, 
                    p.data_origin_id,
                    p.tariff_price, 
                    p.tariff_period, 
                    t.no_subscriptions
            FROM {Product.table_name()} as p
            JOIN {User.table_name()} as a ON p.publisher = a.id
            LEFT JOIN {ProductUsage.table_name()} as pu ON pu.product_id = p.id
            WHERE pu.usage = 1
            LIMIT {limit} OFFSET {start}
        """

    def get_sets_products(self, account_id, subset, where: dict = {}, limit=-1, offset= -1) \
        -> Tuple[Union[dict, list, None], DopError]:
        # NOTE in processor using this function, ensure that 
        # "created_at" (datetime) is serialized correctly
        
        _filter = copy.deepcopy(where)

        product_columns = inspect.signature(Product).parameters
        for key, value in where.items():
            if key in product_columns:
                new_key = 'p.' + key
                _filter[new_key] = where[key]
                _filter.pop(key)
       

        s = subset.get("set")
        if s == "published": 
            query = """    
                SELECT distinct 
                    p.id, 
                    p.label, 
                    p.created_at, 
                    p.data_origin_id,
                    p.tariff_price, 
                    p.tariff_period, 
                    t.no_subscriptions
                FROM {table_product} as p
                JOIN {table_user} as a ON p.publisher = a.id
                LEFT JOIN {product_usage} as pu ON pu.product_id = p.id
            """.format(
                table_product=TableName.PRODUCT,
                table_user=TableName.USER,
                product_usage=TableName.PRODUCT_USAGE
            )
            _filter["pu.usage"] = 1

        elif s == "subscribed":
            query = """    
                SELECT distinct 
                    p.id, 
                    p.label,
                    p.created_at,
                    p.tariff_price, 
                    p.tariff_period, 
                    t.no_subscriptions
                FROM {table_product} as p
                JOIN {table_user} as a ON p.publisher = a.id
                LEFT JOIN {product_usage} as pu ON pu.product_id = p.id
            """.format(
                table_product=TableName.PRODUCT,
                table_user=TableName.USER,
                product_usage=TableName.PRODUCT_USAGE
            )
            _filter["pu.usage"] = 2
        
        _filter["pu.account_id"] = account_id         # TODO Check:left join?
        query = f"""{query} 
                   
                    JOIN (SELECT 
                        p.id as product_id, 
                        count(ps.id) as no_subscriptions
                        FROM {Product.table_name()} as p 
                        LEFT JOIN {ProductSubscription.table_name()} as ps 
                        on p.id = ps.product 
                        GROUP BY p.id) t     
                    ON p.id = t.product_id
                """


        return self._sql_select(query, _filter, limit=limit,offset= offset)

    
    def get_all_products(self, where: dict = None, limit=-1, offset= -1) \
        -> Tuple[Union[dict, list, None], DopError]:
        # NOTE in processor using this function, ensure that 
        # "created_at" (datetime) is serialized correctly
        query = """  
            SELECT p.id,
                p.label, 
                p.created_at,
                p.tariff_price, 
                p.tariff_period,    
                t.no_subscriptions
            FROM {table_product} as p
            JOIN (SELECT 
                        p.id as product_id, 
                        count(ps.id) as no_subscriptions
                        FROM {table_product} as p 
                        LEFT JOIN {table_subscription} as ps 
                        on p.id = ps.product 
                        GROUP BY p.id) t     
                    ON p.id = t.product_id
        """.format(
            table_product=TableName.PRODUCT,
            table_subscription = TableName.PRODUCT_SUBSCRIPTION
        )

        return self._sql_select(query, where, limit=limit,offset= offset)



    def get_other_products(self, account_id, where: dict= None, limit=-1, offset= -1) \
        -> Tuple[Union[dict, list, None], DopError]:
        # NOTE in processor using this function, ensure that 
        # "created_at" (datetime) is serialized correctly

        query = """  
            SELECT distinct p.id,
                p.label, 
                p.created_at,
                p.tariff_price, 
                p.tariff_period
            FROM {table_product} as p
            INNER JOIN {product_usage} as pu
            ON pu.product_id = p.id 
            EXCEPT 
                    SELECT p.id, p.label, p.created_at,
                    p.tariff_price, p.tariff_period
                    FROM {table_product} as p
                    INNER JOIN {product_usage} as pu
                    ON pu.product_id = p.id 
                    AND pu.account_id = ?
                    
        """.format(
            table_product=TableName.PRODUCT,           
            product_usage=TableName.PRODUCT_USAGE
        )


        
        values = [account_id]
        _where = []
        product_columns = inspect.signature(Product).parameters
        for key, value in where.items():

            if key in product_columns:
                new_key = f'p.{key}'
                if value: 
                    _where.append('{attribute}=?'.format(attribute=new_key))
                    values.append(value)

      
        if len(_where): 
            query += " WHERE {where_clause}".format(
                where_clause=' {logic_op} '.format(logic_op='AND').join(_where)
            )
        query += " ORDER BY id"

        if limit != -1 and offset != -1:
            query += f" LIMIT {limit} OFFSET {offset}"

        err, cursor = self._execute_with_retry(query, values)
        if err.isError():
            return [], DopError(106, "An error occurred while executing a select query.")
        try:
            row = cursor.fetchall()
            data = serialize(row, cursor)
        except Exception as e:
            if e.args and len(e.args) > 0:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                        f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
                sys.stderr.flush()
                return [], DopError(107, "An exception occurred while extracting data from the result set.")
            return [], DopError(107,
                             "An exception occurred while extracting data from the result set.")

        # data is a dictionary or a list of dictionaries
        if isinstance(data, dict):
            data = [data]

        for el in data:
            c, err = self.get_number_of_subscriptions(el.get('id'))
            el['no_subscriptions'] = c
        
        return data, DopError()

    def get_number_of_subscriptions(self, product_id)\
        -> Tuple[int, DopError]:
        query = f"""SELECT count(id) 
          FROM {ProductSubscription.table_name()}"""
        where = {'product': product_id} 
        data, err = self._sql_select(query, where)
        if err.isError():
            return -1, err
        return data[0]['count'], err


    
    def get_product_by_blkaddress (self, blkaddress: str) \
            -> Tuple[dict, DopError]: 
        """
            get a product - lookup by blockchain address
            WARNING:    this to be used only internally as it returns the product's secret
            WARNING:    ilike is used as the blk address carried by a log event emitted
                        by a smart contract might be different (lower/upper cases) from
                        an address returned on smart contract creation
        """

        query_product = """
        SELECT          id,
                        label,
                        tariff_price,
                        tariff_period,
                        latitude,
                        longitude,
                        height,
                        elevation,
                        blk_address,
                        blk_specific,
                        city,
                        address,
                        status,
                        publisher,
                        connstring_hostname,
                        connstring_port,
                        connstring_protocol,
                        notes,
                        sensor_type,
                        secret,
                        created_at
        FROM            {table_product}
        WHERE           blk_address ilike '{s_blkaddress}'
        """.format(
            table_product=TableName.PRODUCT,
            s_blkaddress=blkaddress
        )
        products, err = self._sql_select(query_product)
        if err.isError():
            return {}, DopError(305, "The requested product could not be retrieved.")
        
        if len(products) == 0:
            return {}, DopError(0, "The requested product could not be retrieved.")
        
        product = products[0]
        return product, err

     
    def get_session(self, where: dict = None) \
            -> Tuple[Union[Session, list, None], DopError]:
        """
        :param where
        """
        return self._select_obj(Session, where)

     
    def get_user_from_session(self, where: dict) \
            -> Tuple[Union[User, None], DopError]: 
        """
        Get a user from the session string
        """
        session, err = self.get_session(where)
        if err.isError() or session is None:
            return None, err
        
        return self.get_user({'id': session.client})

     
    def get_subscription(self, user_id, product_id: str) \
            -> Tuple[dict, DopError]: 
        """
            get (if any) the subscription of user_id on product_id
        """
        query_subscription: str = """
        SELECT          * 
        FROM            {table_subscriptions} 
        WHERE           subscriber='{uid}'
        AND             product='{pid}'
        """.format(
            table_subscriptions=TableName.PRODUCTS_SUBSCRIBERS,
            uid=user_id,
            pid=product_id
        ) 

        #logger.debug(query_subscription) # TODO logging userdata

        subscriptions, err = self._sql_select(query_subscription)
        if err.isError():
            return {}, DopError(306, "The user's subscription to the indicated product could not be retrieved.")
        
        if len(subscriptions) == 0:
            return {}, DopError(0, "The user's subscription to the indicated product could not be retrieved.")
        
        subscription = subscriptions[0]
        return subscription, err

     
    def get_account_by_blkaddress(self, blkaddress: str) \
            -> Tuple[dict, DopError]: 
        """
            get a user - lookup by blockchain address
            WARNING:    this to be used only internally as it returns blk_password
            WARNING:    ilike is used as the blk address carried by a log event emitted
                        by a smart contract might be different (lower/upper cases) from
                        an address returned by personal.newAccount
        """
        query_account: str = """
        SELECT          {table_account}.id,
                        {table_account}.username,
                        {table_account}.name,
                        {table_account}.blk_address,
                        {table_account}.blk_password
        FROM            {table_account}
        where           {table_account}.blk_address ilike '{s_blkaddress}'
        """.format(
            table_account=TableName.USER,
            s_blkaddress=blkaddress
        )

        #logger.debug(query_account) # TODO a better logging with userdata

        accounts, err = self._sql_select(query_account)
        if err.isError():
            return {}, DopError(308, "The account could not be retrieved.")

        if len(accounts) == 0:
            return {}, DopError(0, "The account could not be retrieved.")

        account = accounts[0]
        return account, err

     
    def get_account_by_session(self, session: str, auth_token: str) \
            -> Tuple[dict, DopError]:
        """
            get a user - lookup by session and token string
        """

        query_account: str = """
        SELECT          {table_account}.id,
                        {table_account}.username,
                        {table_account}.name,
                        {table_account}.blk_address,
                        {table_account}.blk_password
        FROM            {table_account}, {table_session}
        where           {table_session}.value = '{s_session}'
        AND             {table_session}.token = '{s_auth_token}'
        AND             {table_session}.client = {table_account}.id
        """.format(
            table_account=TableName.USER,
            table_session=TableName.SESSION,
            s_session=session,
            s_auth_token=auth_token
        )

        #logger.debug(query_account) # TODO better logging with userdata

        accounts, err = self._sql_select(query_account)
        
        if err.isError():
            return {}, DopError(308, "The account could not be retrieved.")
        
        if  len(accounts) == 0:
            return {}, DopError(0, "The account could not be retrieved.")
        
        account = accounts[0]
        return account, err

     
    def get_transaction_by_hash(self, hash: str) \
            -> Tuple[dict, DopError]: 
        """
            get a transaction object - lookup by hash
            the transaction object holds the following property:
                id, hash, params(null), event_name, client and task
            id:         an integer assigned by the persistence provider
            has:        a string uniquely identifying a pending transaction
            event_name: mnemonic label for the underlying op
            client:     an integer (see account id)
            task:       an integer identifying the underlying op
        """

        query_transaction: str = """
        SELECT          id,
                        hash,
                        params,
                        event_name,
                        client,
                        task, 
                        uuid
        FROM            {table_transaction}
        WHERE           hash ilike '{this_hash}'
        """.format(
            table_transaction=TableName.TRANSACTION,
            this_hash=hash
        )

        #logger.debug(query_transaction) # TODO better logging via userdata

        transactions, err = self._sql_select(query_transaction)
        if err.isError():
            return {}, DopError(309, "The transaction information could not be retrieved.")
        
        if len(transactions) == 0:
            return {}, DopError(0, "The transaction information could not be retrieved.")

        transaction = transactions[0]
        return transaction, err

     
    def get_user_from_username(self, username: str) \
            -> Tuple[Union[User, list, None], DopError]: 
        """
        Get a user object by username
        """
        return self._select_obj(User, {'username': username})

    
    def delete_session(self, id: int) -> DopError: 
        try:
            table_name = Session.table_name()
            query =  "DELETE from {} WHERE id=?;".format(table_name)

            
            err, cursor = self._execute_with_retry(query, (id))

            rows_deleted = cursor.rowcount
            #return DopError(0,f"Deleted rows: {rows_deleted}")
            return DopError()
        except Exception as e:
            if e.args and len(e.args) > 0:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                        f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)

                sys.stderr.flush()
                return DopError(351, "An exception occurred during deletion of session entry.")
            return DopError(351,"An exception occurred during deletion of session entry.")

    
    def delete_encrypted_session(self, session) -> DopError: 
        """   
        """
        try: 
            table_name = EncryptedSession.table_name() 
            query = "DELETE from {} WHERE session_id=?;".format(table_name)
            
            err, cursor = self._execute_with_retry(query, [session])
            rows_deleted = cursor.rowcount
            #return DopError(0, f"Deleted rows {rows_deleted}")
            return DopError(0)
        except Exception as e:
            if e.args and len(e.args) > 0:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                        f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
                sys.stderr.flush()
                return DopError(352, "An exception occurred during deletion of encrypted session entry.")
            return DopError(352, "An exception occurred during deletion of encrypted session entry.")

    

    def delete_transaction(self, transaction_hash: str) -> DopError:
        try:
            table_name = Transaction.table_name()
            query = "DELETE from {} WHERE hash=?;".format(table_name)
            err, cursor = self._execute_with_retry(query, [transaction_hash])
            return err
        # TODO if the _execute_with_retry method is used, there is no exception being thrown 
        # so better check for the error and probably give a more informative info there
        except Exception as e:
            if e.args and len(e.args) > 0:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} |"
                        f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
                sys.stderr.flush()
                return DopError(354, "An exception occurred when deleting the transaction.")
            return DopError(354,"An exception occurred when deleting the transaction.")
        return DopError()

     
    def update_session(self, session_id, **kwargs) -> DopError:
        return self._sql_update(
            Session.table_name(),
            #_where={'client': session_client},
            _where = {'id': session_id},
            update=kwargs)

     
    def update_encrypted_session(self, session, **kwargs) -> DopError : 
        # This update is called when the user connects on a new session_value 
        # the cipher_name, cipher_mode, cipher_keylength, key may need to be updated
        # if the back-end also offers different encodings and integrity checks, those ones 
        # may also be updated

        # TODO Remove from kwargs keys with update not authorized ie id
        return self._sql_update(
            EncryptedSession.table_name(),
            _where={'session_id': session},
            update=kwargs) 


     
    def update_or_create_encrypted_session(self, encSession: EncryptedSession) -> DopError : 
        # insert or update, to be used in the encryption_login processor
        encSession_obj, err = self.get_encrypted_session({'session_id': encSession.session_id})
        if not encSession_obj: 
            _id, err = self._insert_obj(encSession, EncryptedSessionSchema)
            return err
        elif err.isError() or isinstance(encSession_obj, list):
            return DopError(310, "Error while reading encrypted session information.")
        return self.update_encrypted_session(encSession.session_id, **EncryptedSessionSchema().dump(encSession))
    # via multi-session, there should be only an insert_obj here

    
    def create_encrypted_session(self, encSession:  EncryptedSession) -> DopError:
        """
        """
        _id, err = self._insert_obj(encSession, EncryptedSessionSchema)
        return err

      
    def get_encrypted_session(self, where: dict = None) \
            -> Tuple[Union[EncryptedSession, list, None], DopError]: 
        
          
        return self._select_obj(EncryptedSession, where)


    def get_product_summary(self, product_id) -> Tuple[dict, DopError]:
        # NOTE in processor using this function, ensure that 
        # "created_at" (datetime) is serialized correctly

        query_product = """
                SELECT 
                  p.id, 
                  p.label, 
                  p.blk_address,
                  p.publisher,
                  p.created_at,
                  p.tariff_price, 
                  p.tariff_period,
                  a.name as publisher_name
                  FROM {table_product} as p
                  JOIN {product_usage} as tu ON p.id = tu.product_id 
                  JOIN {table_user} as a ON tu.account_id = a.id
                  WHERE p.id = '{product_id}' AND tu.usage = 1
                  """.format(
                    product_id=product_id,
                    table_product=TableName.PRODUCT,
                    product_usage=TableName.PRODUCT_USAGE,
                    table_user=TableName.USER
                  )
       
        products, err = self._sql_select(query_product)
        if err.isError():
            return {}, DopError(312, "The product details could not be retrieved.")

        if len(products) == 0:
            return {}, DopError(0, "The product details could not be retrieved.")    
    
        product = products[0]
        return product, err
         
    
    def get_product_details(self, product_id) -> Tuple[dict, DopError]:
         # TODO improve this
        #   GRAZ
        """
        The following was removed
        SELECT pr.property_value as property_value
        LEFT JOIN {table_property_product} as pp ON pp.product = p.id
        LEFT JOIN {table_property} as pr ON pp.property = pr.id
        """
        query_product = """
                SELECT 
                  p.id,
                  p.blk_address,
                  p.blk_specific,
                  label, 
                  secret,
                  notes,
                  sensor_type,
                  latitude,
                  longitude,
                  address, 
                  city, 
                  height,
                  tariff_price,
                  tariff_period,
                  connstring_protocol,
                  connstring_hostname,
                  connstring_port,
                  status,
                  publisher,
                  a.name as publisher_name, 
                  a.username as publisher_username
                  
                FROM {table_product} as p 
                JOIN {table_user} as a ON p.publisher = a.id
                
                WHERE status=2 AND 
                      p.id='{product_id}'
        """.format(
            product_id=product_id,
            table_product=TableName.PRODUCT,
            table_user=TableName.USER
           )
        products, err = self._sql_select(query_product)
        if err.isError():
            return {}, DopError(312, "The product details could not be retrieved.")

        if len(products) == 0:
            return {}, DopError(0, "The product details could not be retrieved.")
        
        product = products[0]
        return product, err

    
    def get_product_data_origin(self, id) \
        -> Tuple[dict, DopError]:
        query = f"""
            SELECT data_origin_id FROM {Product.table_name()}
        """
        
        data_origin, err = self._sql_select(query, where={"id": id})

        return data_origin,err
    

    def get_property(self, where: dict = None) \
            -> Tuple[Union[Property, list, None], DopError]:
        """
        """
        return self._select_obj(Property, where)


    def create_property(self, property: Property) -> Tuple[int, DopError]:
        _id, err = self._insert_obj(property, PropertySchema)
        return _id, err


    def create_property_product(self, property_product: PropertyProduct) -> DopError:
        _id, err = self._insert_obj(property_product, PropertyProductSchema)
        return err


    
    ########################################################
    # PURPOSE OF USAGE 
    ########################################################
    def create_purpose_of_usage(self, 
                                purpose: PurposeOfUsage)\
                                -> Tuple[int, DopError]:
        _id, err = self._insert_obj(purpose, PurposeOfUsageSchema)
        return _id, err
    
    
    def get_purpose_of_usage(self,
                            where: dict = None) \
                            -> Tuple[list, DopError]: 

        # list of PurposeOfUsage
        try:
            base_query = """
            SELECT * FROM {}
            """.format(PurposeOfUsage.table_name())
            data, err = self._sql_select(base_query,
                                         where,
                                         'AND')
            
            if err.isError():
                return None, err
            if len(data) == 0:
                return [], DopError(0, "Empty result set.")
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            return None, DopError(111, "An exception occurred during select operation.")
        try:
            if isinstance(data, list) and len(data) > 0:
                for element in data:
                    b64_label = element.get('label') 
                    if b64_label is not None:
                        decoded_label, err = DopUtils.from_base64(b64_label)
                        element['label'] = decoded_label
                    b64_url = element.get('url', None)
                    if b64_url is not None:
                        decoded_url, err = DopUtils.from_base64(b64_url)
                        element['url'] = decoded_url
                        

        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            return None, DopError(112, "An exception occurred while mapping extracted data to model.")
        
        return data, DopError()

    def create_product_subscription(self, 
                                    subscription: ProductSubscription)  \
                                    -> Tuple[int, DopError]:
        
        _id, err = self._insert_obj(subscription, ProductSubscriptionSchema)
        if err.isError():
            return 0, err

        product_usage = ProductUsage(
            product_id = subscription.product, 
            account_id = subscription.subscriber,
            usage = 2 # account is subscriber
        )
        err2 = self.create_product_usage(product_usage)
        return _id, err
 
    def get_product_subscription(self, 
                                where: dict = None)\
                                -> Tuple[Union[ProductSubscription, list, None], DopError]: 
        
        return self._select_obj(ProductSubscription, where) 

    def get_additional_info_for_subscriptions(self, where: list = None) \
                -> Tuple[list, DopError]:
        # NOTE in processor using this function, ensure that 
        # "created_at" (datetime) is serialized correctly

        query = f"""SELECT 
                ps.id, 
                ps.purpose_id, 
                ps.created_at,
                pos.label as purpose_label,
                a.name as subscriber_screen, 
                a.id as subscriber_id
                FROM 
                {ProductSubscription.table_name()} as ps
                INNER JOIN {User.table_name()} as a 
                ON ps.subscriber = a.id
                INNER JOIN {PurposeOfUsage.table_name()} as pos
                ON ps.purpose_id = pos.id
                WHERE ps.id IN %s
                """
        
        err, cursor = self._execute_with_retry(query, (tuple(where),))
        
        if err.isError():
            return [], DopError(106, "An error occurred while executing a select query.")
        try:
            row = cursor.fetchall()
            # TODO check: is data always a list?
            data = serialize(row, cursor)
            if isinstance(data, list) and len(data) > 0:
                for element in data:
                    b64_label = element.get('purpose_label') 
                    if b64_label is not None:
                        decoded_label, err = DopUtils.from_base64(b64_label)
                        element['purpose_label'] = decoded_label
        except Exception as e:
            if e.args and len(e.args) > 0:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                        f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
                sys.stderr.flush()
                return [], DopError(107, "An exception occurred while extracting data from the result set.")
            return [], DopError(107,
                             "An exception occurred while extracting data from the result set.")
        
        
        return data, DopError()


   
    def get_additional_info_subscription(self, subscription_id) \
                                -> Tuple[list, DopError]:
        # NOTE in processor using this function, ensure that 
        # "created_at" (datetime) is serialized correctly

        query = f"""SELECT 
                ps.id, 
                ps.purpose_id, 
                ps.created_at,
                pos.label as purpose_label,
                pos.url as purpose_url,
                a.name as subscriber_screen,
                a.id as subscriber_id 
                FROM 
                {ProductSubscription.table_name()} as ps
                INNER JOIN {User.table_name()} as a 
                ON ps.subscriber = a.id
                INNER JOIN {PurposeOfUsage.table_name()} as pos
                ON ps.purpose_id = pos.id 
                """
        try:
           
            data, err = self._sql_select(query, {'ps.id': subscription_id})
                
            if err.isError():
                return None, err
            if len(data) == 0:
                return [], DopError(0, "Empty result set.")
            
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            return None, DopError(111, "An exception occurred during select operation.")
        
        try:
            if isinstance(data, list) and len(data) > 0:
                result = []
                for element in data:
                    self._decode_purpose_prop(element, 'purpose_label')
                    self._decode_purpose_prop(element, 'purpose_url')
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            return None, DopError(112, "An exception occurred while mapping extracted data to model.")

        return data, DopError()


    def get_additional_info_subscription_addr(self, subscription_addr) \
                                -> Tuple[list, DopError]:
        # NOTE in processor using this function, ensure that 
        # "created_at" (datetime) is serialized correctly

        query = f"""SELECT 
                ps.id, 
                ps.purpose_id, 
                ps.created_at,
                CONVERT_FROM(DECODE(pos.label, 'BASE64'), 'UTF-8') as purpose_label, 
                CONVERT_FROM(DECODE(pos.url, 'BASE64'), 'UTF-8') as purpose_url,
                a.name as subscriber_screen,
                a.id as subscriber_id 
                FROM 
                {ProductSubscription.table_name()} as ps
                INNER JOIN {User.table_name()} as a 
                ON ps.subscriber = a.id
                INNER JOIN {PurposeOfUsage.table_name()} as pos
                ON ps.purpose_id = pos.id 
                """
        try:
           
            data, err = self._sql_select(query, {'ps.blk_address': subscription_addr})
                
            if err.isError():
                return None, err
            if len(data) == 0:
                return [], DopError(0, "Empty result set.")
            
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            return None, DopError(111, "An exception occurred during select operation.")
      
        return data, DopError()

    def _decode_purpose_prop(self, entry, prop):
        b64_prop = entry.get(prop) 
        if b64_prop is not None:
            decoded_prop, err = DopUtils.from_base64(b64_prop)
            entry[prop] = decoded_prop
                
    def get_product_subscription_no_secret(self, where: dict = None) \
                                -> Tuple[list, DopError]:
        # NOTE in processor using this function, ensure that 
        # "created_at" (datetime) is serialized correctly

        query = f"""SELECT 
                    ps.id,  
                    ps.subscriber as subscriber_id,
                    ps.product as product_id,
                    ps.purpose_id, 
                    ps.created_at, 
                    a.username as subscriber_name, 
                    a.name as subscriber_screen,
                    pos.label as purpose_label,
                    pos.url as purpose_url
                FROM {ProductSubscription.table_name()} as ps
                INNER JOIN {User.table_name()} as a 
                ON ps.subscriber = a.id
                INNER JOIN {PurposeOfUsage.table_name()} as pos
                ON ps.purpose_id = pos.id
            """
        try:
            _where = {}
            for key, value in where.items():

                new_key = f'ps.{key}'
                if value: 
                    _where[new_key] = value

            data, err = self._sql_select(query, _where, 'AND')
                
            if err.isError():
                return None, err
            if len(data) == 0:
                return [], DopError(0, "Empty result set.")
            
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            return None, DopError(111, "An exception occurred during select operation.")
        try:
            if isinstance(data, list) and len(data) > 0:
                result = []
                for element in data:
                    #created_at = element['created_at']
                    #element['created_at'] = created_at.isoformat()
                    self._decode_purpose_prop(element, 'purpose_label') 
                    self._decode_purpose_prop(element, 'purpose_url')
                    
                    #tmp = ProductSubscription(**element)
                    #result.append(ProductSubscriptionSchema().dump(tmp))
                
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            return None, DopError(112, "An exception occurred while mapping extracted data to model.")
        return data, DopError()

        
    def update_product_subscription(self, 
                                    subscription_id, 
                                    modified_entry: ProductSubscription) \
                                    -> DopError:
        
        return self._sql_update(
            ProductSubscription.table_name(),
            _where={'id': subscription_id}, 
            update=ProductSubscriptionSchema().dump(modified_entry)) 

    def delete_product_subscription(self, 
                                    subscription_id,
                                    subscriber_id,
                                    product_id
                                    ) -> DopError:
        
        # TODO decide on method parameters; the method can be as this one or there can be 
        # only subscription_id as parameter, and a select internally to get 
        # subscriber_id and product_id
        try:
            table_name = ProductSubscription.table_name()
          
            sql = "DELETE from {} WHERE id=?;".format(table_name)
            err, cursor = self._execute_with_retry(sql, [subscription_id])
            if err.isError():
                return err 
            

            # first of all, check if there is more than one product usage entry, 
            # and delete only one entry (at random basically)
            # NOTE there should be as many product_usage entries for this 
            # account for this product as there are product_subscription entries
            where = {
                "account_id" : subscriber_id, 
                "product_id" : product_id,
                "usage" : 2
            }
            usages, err = self.get_product_usage(where)
            if err.isError(): 
                return err 
            
            if isinstance(usages, ProductUsage): 
                usages = [usages]

            # if usages is None? 
            if len(usages):
                to_delete = usages[-1].id 
            
                table_name = ProductUsage.table_name()
                sql2 = "DELETE from {} WHERE id=?;".format(table_name)
                err, cursor = self._execute_with_retry(sql2, [to_delete])
                if err.isError():
                    return err 
                
            return DopError()
        except Exception as e:
            if e.args and len(e.args) > 0:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                        f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
                sys.stderr.flush()
                return DopError(353, "An exception occurred when deleting the subscriber.")      # TODO update: deleting the subscription              
            return DopError(353, "An exception occurred when deleting the subscriber.")

    def insert_account_role(self, account_role: AccountRole) \
                        -> Tuple[int, DopError ]:
        _id, err = self._insert_obj(account_role, AccountRoleSchema)
        return _id, err 

    def get_account_role(self, where:dict = {})\
                        -> Tuple[Union[AccountRole, list, None], DopError]:
        return self._select_obj(AccountRole, where)
    
    def get_account_roles_str(self, where={})\
                        -> Tuple[list, DopError]:
        
        query = f"""
            SELECT role 
            FROM {AccountRole.table_name()}
        """
        data, err = self._sql_select(query, where)
        
        if err.isError():
            return None, err
        if len(data) == 0:
            return [], DopError(0, "Empty result set.")

        return data, DopError()
            

    def delete_account_role(self, id) -> DopError:
        try:
            table_name = AccountRole.table_name()
            query =  "DELETE from {} WHERE id=?;".format(table_name)

            
            err, cursor = self._execute_with_retry(query, (id))

            rows_deleted = cursor.rowcount
            #return DopError(0,f"Deleted rows: {rows_deleted}")
            return DopError()
        except Exception as e:
            if e.args and len(e.args) > 0:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                        f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)

                sys.stderr.flush()
                return DopError(355, "An exception occurred during deletion of account role entry.")
            return DopError(355,"An exception occurred during deletion of account role entry.")


    # PRIVATE METHODS 
    
    def _execute(self, cursor, query, values=None):
        if not values:
            values = []
        try:
            cursor.execute(str(query), values)
        except pyodbc.Error as e: 

            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            if "internal SAVEPOINT failed" in e.args[1]:
                self.open()
            
            if isinstance(e, pyodbc.IntegrityError):
                return DopError(104, "An integrity error occurred while executing a query.")
        
            if isinstance(e, pyodbc.OperationalError):
                return DopError(105, "An error occurred while executing a query.")
    

            return DopError(105, "An error occurred while executing a query.")
                
        #except pyodbc.IntegrityError as err:
        #    print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
        #                     f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
        #    sys.stderr.flush()
        #except pyodbc.OperationalError as oe:
        #    print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
        #                     f"{getframeinfo(currentframe()).lineno} | {type(oe)} | {traceback.format_exc()}", file = sys.stderr)
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            return DopError(105, "An error occurred while executing a query.")
        return DopError()

    def _cursor(self) -> Tuple[DopError, pyodbc.Cursor]:
        cursor = None
        max_retry = self._recovery_max      
        while max_retry > 0:       
            err = self.open()
            if err.isError():
                return err, None     
            try:
                cursor = self._connection.cursor()
            except Exception as e:
                if self._recoverable(e):
                    max_retry -= 1
                    print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                            f"{getframeinfo(currentframe()).lineno} | Recovering from last error. Retries left: {max_retry}.\n", file = sys.stderr)
                    self.close()
                    self._recovery_delay()
                    continue
                return DopError(123, "Non recoverable error while getting database cursor."), cursor  # not recoverable
            return DopError(0), cursor      # success
        return DopError(124,"Non recoverable error while getting database cursor: maximum number of attempts exceeded" ), cursor      


    def _execute_with_retry(self, query, values=None) -> Tuple[DopError, pyodbc.Cursor]:
        max_retry = self._recovery_max
        cursor = None
        while max_retry > 0: 
            err = self.open()
            if err.isError():
                return err, cursor
            err, cursor = self._cursor() 

            if err.isError():
                return err, cursor
            
            try:
                cursor.execute(str(query), values)
                #cursor.commit()
                #cursor.close()      
            except pyodbc.Error as e: 
                if self._recoverable(e):
                    max_retry -= 1
                    print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                            f"{getframeinfo(currentframe()).lineno} | Recovering from last error. Retries left: {max_retry}.\n", file = sys.stderr)
                    self.close()
                    self._recovery_delay()
                    continue
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                            f"{getframeinfo(currentframe()).lineno} | Error: {e}\n", file = sys.stderr)
                    
                return DopError(121, "Non recoverable error while executing a query."), cursor # not recoverable
            return DopError(0), cursor    #  success
        return DopError(122, "Query could not be executed: maximum number of attempts exceeded."), cursor

    def _sql_select(self, base_query, where: dict = None, logic_op: str = 'AND', limit=-1, offset=-1) \
            -> Tuple[list, DopError]:
      
        query = base_query
        # TODO Select with columns name
        values = []
        _where = []
        if where:
            for attribute, value in where.items():
                if value:
                    _where.append('{attribute}=?'.format(attribute=attribute))
                    values.append(value)
            where_clause = ' {logic_op} '.format(logic_op=logic_op).join(_where)
            query += " WHERE {where_clause}".format(
                where_clause=where_clause
            )
        if limit != -1 and offset != -1:
            query += f" LIMIT {limit} OFFSET {offset} "
        err, cursor = self._execute_with_retry(query, values)
        if err.isError():
            return [], DopError(106, "An error occurred while executing a select query.")
        try:
            row = cursor.fetchall()
            data = serialize(row, cursor)
        except Exception as e:
            if e.args and len(e.args) > 0:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                        f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
                sys.stderr.flush()
                return [], DopError(107, "An exception occurred while extracting data from the result set.")
            return [], DopError(107,
                             "An exception occurred while extracting data from the result set.")

        return data, DopError()

    def _sql_update(self, table_name, _where: dict, update: dict):
        values = []
        _set = []
        where = []
        for key, value in update.items():
            if value:
                values.append(value)
                _set.append('{key} = ?'.format(key=key))
        for attribute, value in _where.items():
            if value:
                where.append('{attribute}=?'.format(attribute=attribute))
                values.append(value)
            else:
                return DopError(1)
        if len(values) == 0:
            # TODO check if this is to be considered and error
            return DopError(108, "No update requested")
        try:
            query = 'UPDATE {} '.format(
                table_name) + ' SET ' + ','.join(_set) + ' WHERE ' + ' AND '.join(where)
            c = self._connection.cursor()
            # self._execute(c, query, values)
            err, cursor = self._execute_with_retry(query, values)
            if err.isError():
                return err
        except Exception as e:
            if e.args and len(e.args) > 0:
                print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                        f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
                sys.stderr.flush()
                return DopError(109, "An exception occurred during update operation: impossible to update the element.")
            return DopError(109, "An exception occurred during update operation: impossible to update the element.")
        return DopError()

    def _sql_insert(self, table_name, obj: dict) -> Tuple[Union[int, None], DopError]:
      
        query = "INSERT INTO {} ".format(table_name)
        cols = []
        values = []
        params = []
        for attribute, value in obj.items():
            if value:
                cols.append(attribute)
                params.append('?')
                values.append(value)
        cols = ' (' + ", ".join(cols) + ')'
        params = ' (' + ', '.join(params) + ')'
        query += cols + ' VALUES ' + params
        query += ' RETURNING id;'
        try:
            err, cursor = self._execute_with_retry(query, values)
        except pyodbc.IntegrityError as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            raise
        except Exception as e: 
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            return None, DopError(110, "An exception occurred during insert operation.")

        if err.isError():
            return None, err
        _id = cursor.fetchall()
        #logger.debug(_id[0]) # TODO better logging management - userdata
        #logger.debug(_id[0][0]) # TODO better logging management - userdata
        return _id[0][0], err

    def _select_obj(self, model: Type[Model], where_clause: dict, logic_op: str = 'AND') \
            -> Tuple[Union[list, Model, None], DopError]:
       
        try:
            base_query = """
            SELECT * FROM {}
            """.format(model.table_name())
            data, err = self._sql_select(base_query,
                                         where_clause,
                                         logic_op)
            
            if err.isError():
                return None, err
            if len(data) == 0:
                return None, DopError(0, "Empty result set.")
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            return None, DopError(111, "An exception occurred during select operation.")
        try:
            # TODO try with schema load / postload
            if isinstance(data, list) and len(data) > 1:
                result = []
                for element in data:
                    tmp = model(**element)
                    result.append(tmp)
            else:
                result = model(**data[0])
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            return None, DopError(112, "An exception occurred while mapping extracted data to model.")
        return result, DopError()

    def _insert_obj(self, model, schema) -> Tuple[Union[int, None], DopError]:
        try:
            obj = schema().dump(model)
            _id, err = self._sql_insert(model.table_name(), obj)
            if err.isError():
                return None, err
        except pyodbc.IntegrityError as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            return None, DopError(113, "Error in insert: integrity constraint violated.")
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()
            return None, DopError(114, "Insert query error.")
        return _id, DopError()