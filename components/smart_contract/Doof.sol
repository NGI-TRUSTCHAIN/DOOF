//SPDX-License-Identifier: Apache-2.0
/*
    © Copyright Ecosteer 2024
    auth:	graz
    ver:	0.2
    date:	26/06/2024
*/

pragma solidity ^0.5.0;


contract Doof {    

    //  the following macros' values will have to be used
    //  by the upper application layer (avoid enums)
    uint public constant SLOT_GLOBAL    = 0;        //  slot selector (GLOBAL)
    uint public constant SLOT_VAULT     = 1;        //  slot selector (VAULT)
    uint public constant SLOT_PROXY     = 2;        //  slot selector (PROXY)
    uint public constant SLOT_URL       = 3;        //  slot selecto (URL)
    uint public constant STATUS_GRANTED = 1;        //  used by subscriptionStatusSet
    uint public constant STATUS_REVOKED = 0;        //  used by subscriptionStatusSet

    //  error codes
    //  the following macros' values will have to be used
    //  by the upper application layer (avoid enums)
    uint public constant ERR_OK         = 0;
    uint public constant ERR_OK_NOLOG   = 1;        //  introduced to avoid emitting grant/revoke log when new status is equal to old status
    uint public constant ERR_MEMBER_DNE = 100;      //  member does not exist
    uint public constant ERR_MEMBER_DNA = 101;      //  member does not authenticate
    uint public constant ERR_MEMBER_NPE = 102;      //  member not enough privileges
    uint public constant ERR_MEMBER_AEX = 103;      //  memebr exists already
    uint public constant ERR_PAYEE_DNE  = 104;
    uint public constant ERR_SUPPL_DNE  = 105;
    uint public constant ERR_SUPPL_DNA  = 106;
    uint public constant ERR_SUBSCR_DNE = 200;      //  subscription does not exist
    uint public constant ERR_SUBSCR_AEX = 201;      //  subscription exists already
    uint public constant ERR_SUBSCR_DNM = 202;      //  subscription does not match
    uint public constant ERR_PROD_DNE   = 300;      //  product does not exists
    uint public constant ERR_PROD_SNV   = 301;      //  product slot selector not valid
    uint public constant ERR_PROD_AEX   = 302;      //  product already exists
    uint public constant ERR_RANGE_OUT  = 400;      //  out of range
    uint public constant ERR_STATUS_INV = 500;      //  invalid status
    uint public constant ERR_RESERV_INE = 600;      //  reserve is not enough


    struct Head {
        address     owner;                  //  the owner (blockchain account) of this marketplace
        bytes32     secret;                 //  secret
        uint256     reserve;                //  total amount of available tokens (within this marketplace instance)
        uint256     airdrop;                //  the amount to be airdropped to the new member
    }

    struct Member {
        bool            defined;            //  facilitates mapping lookup
        bytes32         secret;             //  the member's root secret (keccak256)
        bytes32         proxy_secret;       //  the member's proxy secret (keccak256)
        uint256         balance;            //  the member balance
    }

    struct Subscription {
        bool        defined;
        bytes32     addr;                   //  address of this subscription
        bytes32     addr_product;           //  the address (mapping key) of the product
        bytes32     addr_subscriber;        //  the address (mapping key) of the subscriber
        uint        status;
        uint256     credit;
        uint256     debit;
        uint256     usage;
        uint256     tog;
        uint256     last_charge;
    }

    struct Product {
        bool        defined;
        bytes32     addr_owner;             //  the address (mapping key) of the member owner of the product
        bytes32     addr_payee;             //  the address (mapping key) of the member that can be credited (from the product balance)
        string[4]   vault;                  //  product memory slots (proxy, global, vault, url)
        bytes32[]   arr_subscriptions;      //  array of the addresses (mapping keys) of the subscriptions for this product
                                            //  the addr_subscriptions facilitates charge and accrue batch oriented ops
                                            //  to be fire for each product, for all the subscriptions to the product

        uint256     balance;                //  the product balance (accrued from all the product's subscriptions)
        uint256     price;                  //  price of period
        uint256     period;                 //  period in seconds

    }

    //  Note:   the mapping keys (of type bytes32) are always bytes32 returned by keccak256(UUID)
    //          where the UUID is responsibility of the upper solution layer (e.g. DOOF worker)

    mapping(bytes32 => Product)         i_map_products;         //  mapping of all the products within this marketplace instance
    bytes32[]                           i_arr_products;         //  array of all the products' addresses within this marketplace instance
                                                                //  the addr_products facilitates products' set walkthrough ops (such as charge and accrual)

    mapping(bytes32 => Subscription)    i_map_subscriptions;    //  mapping of all the subscriptions within the marketplace
                                                                //  optimizes access to subscriptions for e.g. P.E.T. driven ops

    mapping(bytes32 => Member)          i_map_members;          //  mapping of all the members within this marketplace
    bytes32[]                           i_arr_members;

    Head i_head;    //  to be initialized by the constructor


    //  modifiers
    modifier RootOnly() {require (msg.sender==i_head.owner, "Sender not allowed"); _;}

    //  events
    event LogMemberCreate(
        address _marketplace                //  smart contract address (address of the marketplace)
    ,   bytes32 _account_mkt_address        //  account (created one) marketplace address (use this to reference the account)
    ,   bytes32 _err_code                      //  operation result (0 if successfull)
    );

    event LogProductCreate(
        address _marketplace                //  smart contract address (address of the marketplace)
    ,   bytes32 _product_mkt_address        //  product (created one) marketplace address (use this to reference the product)
    ,   bytes32 _err_code                      //  operation result (0 if successfull)
    );

    event LogSubscriptionCreate(
        address _marketplace
    ,   bytes32 _subscription_mkt_address   //  subscription (created one) marketplace address (use this to reference the subscription)
    ,   bytes32 _err_code
    );

    event LogProductUpdate(
        address _marketplace
    ,   bytes32 _product_marketplace_address
    ,   bytes32 _err_code
    );

    event LogSubscriptionGranted(
        address _marketplace
    ,   bytes32 _subscription_mkt_address   //  subscription that has been granted
    ,   bytes32 _err_code
    );

    event LogSubscriptionRevoked(
        address _marketplace
    ,   bytes32 _subscription_mkt_address   //  subscription that has been revoked
    ,   bytes32 _err_code
    );

    event LogSubscriptionDelete(
        address _marketplace
    ,   bytes32 _subscription_mkt_address   //  subscription deleted
    ,   bytes32 _err_code
    );

  
    constructor (
        string memory   a_secret,               //  marketplace owner secret
        uint256         a_reserve,              //  total reserve to be assigned to the marketplace
        uint256         a_airdrop               //  amount to be airdropped to the new member
    ) public
    {
        //  initializes the smart contract Head
        i_head.owner = msg.sender;
        i_head.secret = keccak256(bytes(a_secret));        //  calculate and set the marketplace owner secret
        i_head.reserve = a_reserve;
        i_head.airdrop = a_airdrop;
    }

    //  ==============================================================
    //      utility methods
    //  ==============================================================
    function marketplaceAddress (
        string memory addr
    ) public pure returns (bytes32)
    {
        //  convert a solution layer address (e.g. a UUID) into a marketplace (smart contract) address
        //  this is useful to simplify the way the solution layer can access a Member, a Product, etc.
        bytes memory m_address = bytes(addr);
        bytes32 s_address = keccak256(m_address);
        return (s_address);
    }

    function marketplaceHash (
        string memory data
    ) public pure returns (bytes32)
    {
        //  applies keccak256 to a string and returns the bytes32 (result from keccack256)
        bytes memory m_data = bytes(data);
        return (keccak256(m_data));
    }

    function validStatus(uint status) internal pure returns (uint err)
    {
        err = ERR_OK;
        bool valid = false;
        valid = (status == STATUS_GRANTED) || (status == STATUS_REVOKED);
        if (valid == false) { err=ERR_STATUS_INV; }
        return (err);
    }

    function validSelector(uint slot_selector) internal pure returns (uint err)
    {
        err = ERR_OK;
        bool valid = false;
        valid = (slot_selector == SLOT_GLOBAL)  ||
                (slot_selector == SLOT_VAULT)   ||
                (slot_selector == SLOT_PROXY)   ||
                (slot_selector == SLOT_URL);
        if (valid == false) { err = ERR_PROD_SNV; }
        return err;
    }


    function removeItem(
        bytes32[] storage   items,
        bytes32             a_mkt_subscription
    ) internal returns (uint err)
    {
        //  general purpose method to delete an item in an array
        //  this method is used to remove a subscritions form the
        //  product's subscriptions array
        
        err = ERR_OK;
        uint len = items.length;
        for (uint index=0; index < len; index++)
        {   
            if (items[index] == a_mkt_subscription)
            {
                //  the item to be delete has been found - the following lines optimize the array layout
                //  this might not be necessary, but it is considered to be good practice
                len--;
                for (;index<len;index++) { items[index] = items[index+1]; }
                delete items[len];
                items.length--;
                return(err);
            }
        }
        return(ERR_SUBSCR_DNE);
    }



    //  ==============================================================
    //      membership methods
    //  ==============================================================
    function members() public RootOnly view returns(bytes32[] memory) 
    {
        //  this method mainly to support upper application layer and for testing purposes
        return i_arr_members;
    }

    function memberCount () public view returns (uint)
    {
        //  returns the number of members within the marketplace
        uint len = i_arr_members.length;
        return (len);
    }

    function memberAddress(uint index) public view returns (uint err, bytes32 addr)
    {
        //  returns the member marketplace address (bytes32) at the given index
        err = ERR_OK;
        addr = bytes32('0x0');

        if (index >= i_arr_members.length)
        {
            //  out of range
            err = ERR_RANGE_OUT;
            return (err,addr);
        }
        addr = i_arr_members[index];
        return (err,addr);
    }


    function memberCreate (
        string memory   a_address,              //  tipically a UUID generated by the upper layer
        string memory   a_secret,
        string memory   a_proxy_secret               
    ) public RootOnly returns (uint err, bytes32 addr)
    {
        //  NOTE:   the a_address is responsibility of the upper layer and typically it is a UUID
        //          the returned value will be the address of the member within the marketplace


        err = ERR_OK;
        addr = bytes32('0x0');
        bytes32 s_key = marketplaceAddress(a_address);          //  s_key is marketplace member address
        bytes32 s_secret        = marketplaceHash(a_secret);
        bytes32 s_proxy_secret  = marketplaceHash(a_proxy_secret);

        //  check if there is enough reserve
        if (i_head.reserve < i_head.airdrop) 
        {
            err = ERR_RESERV_INE;
            emit LogMemberCreate(address(this),addr,bytes32(err));
            return(err, addr);
        }

        //  reserve is enough
        i_head.reserve = i_head.reserve - i_head.airdrop;
        Member storage account = i_map_members[s_key];
        if (account.defined == true) 
        {
            err = ERR_MEMBER_AEX;
            emit LogMemberCreate(address(this), s_key, bytes32(err));
            return (err, addr);
        }

        //  the address has not been used, yet
        account.defined = true;
        account.balance = i_head.airdrop;
        account.secret = s_secret;
        account.proxy_secret = s_proxy_secret;

        i_arr_members.push(s_key);
        err = ERR_OK;
        addr = s_key;

        //  emit AccountCreate log event
        emit LogMemberCreate(address(this), s_key, bytes32(err));
        return(err, addr);
    }

    function memberInfo (
        bytes32         a_addr_account,             //  address of the account the supplicant wants to know about
        bytes32         a_addr_supplicant,          //  address of the supplicant
        string memory   a_supplicant_proxy_secret   //  supplicant proxy secret
    ) public view returns (uint err, uint256 val)
    {
        //  check if the account exists
        Member storage account = i_map_members[a_addr_account];
        Member storage supplicant = i_map_members[a_addr_supplicant];
        if (account.defined != true) return (ERR_MEMBER_DNE,0);
        if (supplicant.defined != true) return (ERR_SUPPL_DNE,0);

        bytes32 m_proxy_secret = marketplaceHash(a_supplicant_proxy_secret);
        if (m_proxy_secret != supplicant.proxy_secret) return (ERR_SUPPL_DNA,0);
        return (0,account.balance);
    }


    function memberAuthenticate (
        bytes32         a_addr_member,
        string memory   a_member_secret,
        uint            a_type              //  0 checks proxy_secret, anything else checks secret
    ) public view returns (uint err)
    {
        err = ERR_OK;
        Member storage member = i_map_members[a_addr_member];
        if (member.defined != true) 
        {
            //  member does not exist
            err = ERR_MEMBER_DNE;
            return (err);
        }
        //  member available
        bytes32 s_member_secret = marketplaceHash(a_member_secret);

        bytes32 member_secret;
        bool isproxy = (a_type == 0);
        
        if (isproxy) { member_secret = member.proxy_secret; }
        else member_secret = member.secret;

        if (s_member_secret != member_secret) 
        {   
            //  the secrets do not match, member does not authenticate
            err = ERR_MEMBER_DNA; 
        }

        return (err);
    }



    //  ==============================================================
    //      products methods
    //  ==============================================================
    function products() public RootOnly view returns(bytes32[] memory) 
    {
        //  this method mainly to support upper application layer and for testing purposes
        return i_arr_products;
    }


    function productAddress(uint index) public view returns (uint err, bytes32 addr)
    {
        //  returns the product marketplace address (bytes32) at the given index
        err = ERR_OK;
        if (index >= i_arr_products.length) 
        {
            //  out of range
            err=ERR_RANGE_OUT;
            return (err,bytes32(err));
        }
        return (ERR_OK,i_arr_products[index]);
    }


    function productGet (
        bytes32         p_mkt_address,                  //  product marketplace address
        uint            slot_selector,  
        bytes32         a_mkt_supplicant,               //  supplicant marketplace address
        string memory   a_supplicant_proxy_secret
    ) public view returns (uint err, string memory vault)
    {
        err = ERR_OK;
        vault = "";

        err = validSelector(slot_selector);
        if (err != ERR_OK)
        {
            //  invalid slot selector
            return (err,vault);
        }

        //  valid selector
        err = memberAuthenticate(a_mkt_supplicant, a_supplicant_proxy_secret, 0);
        if (err != ERR_OK)
        {
            return (err,vault);
        }

        //  supplicant authenticated
        //  get product's storage
        Product storage product = i_map_products[p_mkt_address];
        if (product.defined != true)
        {   
            //  product does not exist
            err = ERR_PROD_DNE;
            return (err,vault);
        }
        
        //  product exists
        vault = product.vault[slot_selector];
        return (err,vault);
    }

    function productUpdate (
        bytes32         p_mkt_address,                  //  product marketplace address
        uint            slot_selector,
        string memory   a_owner_proxy_secret,
        string memory   new_data
    ) public returns (uint err)
    {
        err = ERR_OK;
        err = validSelector(slot_selector);
        if (err != ERR_OK)
        {
            //  invalid slot selector
            emit LogProductUpdate(address(this),p_mkt_address,bytes32(err));
            return (err);
        }

        //  get product's storage
        Product storage product = i_map_products[p_mkt_address];
        if (product.defined != true)
        {   
            //  product does not exist
            err = ERR_PROD_DNE;
            emit LogProductUpdate(address(this),p_mkt_address,bytes32(err));
            return (err);
        }

        //  the product exists
        //  check if the the secret is the product owner proxy secret
        err = memberAuthenticate(product.addr_owner, a_owner_proxy_secret, 0);
        if (err != ERR_OK)
        {
            emit LogProductUpdate(address(this),p_mkt_address,bytes32(err));
            return (err);
        }

        //  valid slot selector, update the selected slot
        product.vault[slot_selector] = new_data;

        emit LogProductUpdate(address(this),p_mkt_address,bytes32(err));
        return (err);
    }



    function productSubscriptions(
        bytes32         a_mkt_product,
        bytes32         a_mkt_supplicant,
        string memory   supplicant_proxy_secret
    ) public view returns(uint err, bytes32[] memory) {
        err = ERR_OK;
        bytes32[] memory arr = new bytes32[](0);

        Product storage product = i_map_products[a_mkt_product];
        if (product.defined != true)
        {
            err=ERR_PROD_DNE;
            return(err,arr);
        }

        err = memberAuthenticate(a_mkt_supplicant, supplicant_proxy_secret, 0);
        if (err != ERR_OK)
        {
            return (err,arr);
        }
        return (err,product.arr_subscriptions);
    }

    function productInfo(
        bytes32         a_mkt_product,                  //  marketplace address of the product
        bytes32         a_mkt_supplicant,               //  marketplace address of the supplicant
        string memory   supplicant_proxy_secret
    ) public view returns (uint err, bytes32 owner, bytes32 payee, uint256 balance, uint256 price, uint256 period)
    {
        err = ERR_OK;
        owner = bytes32('0x0');
        payee = bytes32('0x0');
        balance = 0;
        price = 0;
        period = 0;

        //  check if product has been defined
        Product storage product = i_map_products[a_mkt_product];
        if (product.defined != true)
        {
            err = ERR_PROD_DNE;
            return (err, owner, payee, balance, price, period);
        }

        err = memberAuthenticate(a_mkt_supplicant, supplicant_proxy_secret, 0);
        if (err != ERR_OK)
        {
            //  memberAuthenticate sets the err
            return (err, owner, payee, balance, price, period);
        }

        owner = product.addr_owner;
        payee = product.addr_payee;
        balance = product.balance;
        price = product.price;
        period = product.period;
        return (err, owner, payee, balance, price, period);
    }

    function productCreate (
        string memory   a_address,                  //  the address assigned by the upper layer (typically a UUID)
        bytes32         a_addr_owner,               //  the marketplace address of the product's owner
        bytes32         a_addr_payee,               //  the marketplace address of the product's payee
        string memory   a_owner_proxy_secret,       //  the proxy secret of the product's owner
        uint256         a_price,
        uint256         a_period
    ) public returns (uint err, bytes32 addr)
    {
        err = ERR_OK;
        addr = bytes32('0x0');

        bytes32 m_address = marketplaceAddress(a_address);
        Product storage product = i_map_products[m_address];
        if (product.defined == true)
        {   
            //  product address in use already
            err = ERR_PROD_AEX;
            emit LogProductCreate(address(this),m_address,bytes32(err));
            return (err,m_address);
        }

        //  product address available
        //  check if owner is available and if the secret matches
        
        err = memberAuthenticate(a_addr_owner, a_owner_proxy_secret, 0);

        if (err != ERR_OK)
        {
            emit LogProductCreate(address(this),m_address,bytes32(err));
            return (err, a_addr_owner);
        }

        //  owner exists and the proxy_secret matches        
        //  check if the payee is available
        Member storage payee = i_map_members[a_addr_payee];
        if (payee.defined != true)
        {
            //  payee not available
            err = ERR_PAYEE_DNE;
            emit LogProductCreate(address(this),m_address,bytes32(err));
            return(err,a_addr_payee);
        }

        //  everything ok
        //  the product can be created
        product.defined = true;
        product.addr_owner = a_addr_owner;
        product.addr_payee = a_addr_payee;
        product.balance = 0;
        product.price = a_price;
        product.period = a_period;

        i_arr_products.push(m_address);

        emit LogProductCreate(address(this),m_address,bytes32(err));
        return (err, m_address);
    }


    
    //  ==============================================================
    //      subscriptions methods
    //  ==============================================================

    function subscriptionDelete(
        bytes32         a_mkt_subscription              //  marketplace address of the subscription to be deleted
    ,   bytes32         a_mkt_product                   //  marketplace address of the product referenced by the subscription
    ,   bytes32         a_mkt_subscriber                //  marketplace address of the subscriber
    ,   string memory   sub_proxy_secret                //  proxy secret of the subscriber
    ) public returns (uint err, bytes32 sub_addr)
    {
        //  only the subscriber can delete her subscription

        err = ERR_OK;
        sub_addr = a_mkt_subscription;

        //  find the referenced subscription
        Subscription storage subscription = i_map_subscriptions[a_mkt_subscription];
        if (subscription.defined != true)
        {
            //  the subscription does not exist
            err = ERR_SUBSCR_DNE;
            emit LogSubscriptionDelete(address(this),sub_addr,bytes32(err));
            return(err,sub_addr);
        }

        //  the subscription has been found
        //  check if the supplicant is the owner of the subscription
        if (subscription.addr_subscriber != a_mkt_subscriber)
        {
            //  the supplicant does not own the subscription
            err=ERR_MEMBER_NPE;
            emit LogSubscriptionDelete(address(this),sub_addr,bytes32(err));
            return(err,sub_addr);
        }

        //  check if the subscription holds the reference to the right product
        if (subscription.addr_product != a_mkt_product)
        {
            //  the referenced product does not match
            err = ERR_SUBSCR_DNM;
            emit LogSubscriptionDelete(address(this),sub_addr,bytes32(err));
            return(err,sub_addr);
        }

        //  the product matches, check if the subscribers authenticates
        err = memberAuthenticate(a_mkt_subscriber, sub_proxy_secret, 0);
        if (err != ERR_OK)
        {
            //  the subscriber does not exists or it does not authenticate
            emit LogSubscriptionDelete(address(this),sub_addr, bytes32(err));
            return(err, sub_addr);
        }

        //  the subscription can be deleted
        //  delete the subscription from the subscriptions' map
        subscription.defined = false;
        delete i_map_subscriptions[a_mkt_subscription];
        //  delete the subscriptions from the product's subscriptions array
        Product storage product = i_map_products[a_mkt_product];
        if (product.defined == true)
        {
            removeItem(product.arr_subscriptions,a_mkt_subscription);
        }
        
        emit LogSubscriptionDelete(address(this),sub_addr, bytes32(err));
        return(err, sub_addr);
    }


    function subscriptionCreate(
        string memory   a_address           //  application layer uinque identifier (typically a UUID)
    ,   bytes32         product_address     //  marketplace address of product referenced by the subscription
    ,   bytes32         sub_address         //  marketplace address of subscriber
    ,   string memory   sub_proxy_secret    //  subscriber proxy secret
    ) public returns (uint err, bytes32 addr)
    {
        err = ERR_OK;
        addr = marketplaceAddress(a_address);

        //  check if the subscriber exists
        err = memberAuthenticate(sub_address, sub_proxy_secret, 0);
        if (err != ERR_OK)
        {
            //  the subscriber does not exists or it does not authenticate
            emit LogSubscriptionCreate(address(this),addr, bytes32(err));
            return(err, addr);
        }

        //  the member exists and the member authenticates
        //  check if the product exists
        Product storage product = i_map_products[product_address];
        if (product.defined != true) 
        {
            //  the product does not exist
            err = ERR_PROD_DNE;
            emit LogSubscriptionCreate(address(this),addr,bytes32(err));
            return(err, addr);
        }

        //  check if the subscription exists already
        Subscription storage subscription = i_map_subscriptions[addr];
        if (subscription.defined == true)
        {
            //  the subscription exists already
            err = ERR_SUBSCR_AEX;
            emit LogSubscriptionCreate(address(this),addr,bytes32(err));
            return(err,addr);
        }

        //  the subscription did not exists, so it can be created
        subscription.defined            = true;
        subscription.addr               = addr;
        subscription.addr_product       = product_address;
        subscription.addr_subscriber    = sub_address;
        subscription.tog                = 0;
        subscription.status             = STATUS_REVOKED;
        subscription.credit             = 0;
        subscription.debit              = 0;
        subscription.usage              = 0;
        subscription.last_charge        = 0;

        //  add the subscription to the product's subscriptions array
        product.arr_subscriptions.push(addr);
        emit LogSubscriptionCreate(address(this),addr,bytes32(err));
        return(err,addr);
    }

    function subscriptionInfo (
        bytes32             a_mkt_subscription,
        bytes32             a_mkt_supplicant,
        string memory       supplicant_proxy_secret
    ) public view returns (uint err, bytes32 product, bytes32 subscriber, uint256 tog, uint status)
    {
        err=ERR_OK;
        product = bytes32('0x0');
        subscriber = bytes32('0x0');
        tog = 0;
        status = STATUS_REVOKED;

        Subscription storage subscription = i_map_subscriptions[a_mkt_subscription];
        if (subscription.defined != true)
        {
            err=ERR_SUBSCR_DNE;
            return(err,product,subscriber,tog,status);
        }
        //  the subscription has been found
        //  check supplicant
        err = memberAuthenticate(a_mkt_supplicant,supplicant_proxy_secret,0);
        if (err!=ERR_OK)
        {
            return(err,product,subscriber,tog,status);
        }

        product     = subscription.addr_product;
        subscriber  = subscription.addr_subscriber;
        tog         = subscription.tog;
        status      = subscription.status;

        return(err,product,subscriber,tog,status);
    }




    function subscriptionStatusGet(
        bytes32         a_mkt_subscription,         //  marketplace address of the subscription
        bytes32         a_mkt_supplicant,
        string memory   a_supplicant_proxy_secret   //  proxy secret of the product referenced by the subscription
    ) public view returns (uint err, uint status, uint256 tog)
    {
        err = ERR_OK;
        tog = 0;
        status = STATUS_REVOKED;

        //  find the subscription
        Subscription storage subscription = i_map_subscriptions[a_mkt_subscription];
        if (subscription.defined != true)
        {
            //  the subscription does not exist
            err = ERR_SUBSCR_DNE;
            return(err,status,tog);
        }


        //  subscription exists, authenticate the supplicant
        err = memberAuthenticate(a_mkt_supplicant, a_supplicant_proxy_secret, 0);
        if (err != ERR_OK)
        {
            return(err,status,tog);
        }

        status = subscription.status;
        tog = subscription.tog;
        return (err,status,tog);
    }



    function subscriptionStatusSet(
        bytes32         a_mkt_subscription,         //  marketplace address of the subscription
        string memory   a_owner_proxy_secret,       //  proxy secret of the product referenced by the subscription
        uint            new_status                  //  STATUS_GRANTED, STATUS_REVOKED
    ) internal returns (uint err)
    {
        err = validStatus(new_status);
        if (err != ERR_OK)
        {
            //  invalid new status
            return (err);
        }

        //  find the subscription
        Subscription storage subscription = i_map_subscriptions[a_mkt_subscription];
        if (subscription.defined != true)
        {
            //  the subscription does not exist
            err = ERR_SUBSCR_DNE;
            return(err);
        }

        //  check if the new_status is different from the previous status
        if (subscription.status == new_status)
        {
            //  nothing to do here - stop wasting resources
            err = ERR_OK_NOLOG;
            return(err);    // no error
        }

        //  the subscription exists, find the product (to get the onwer of the product)
        Product storage product = i_map_products[subscription.addr_product];
        if (product.defined != true)
        {
            //  strange :) the product does not exist
            err = ERR_PROD_DNE;
            return(err);
        }

        //  product exists, authenticate supplicant (must be product owner)
        err = memberAuthenticate(product.addr_owner, a_owner_proxy_secret, 0);
        if (err != ERR_OK)
        {
            return(err);
        }

        //  ok the the status of the subscription can be changed
        subscription.status = new_status;
        if (new_status == STATUS_GRANTED) 
        {
            //  if the status changes to granted, then the tog has to be updated, too
            //  NOTE: block.timestamp can be set by miners (within certain limit)
            subscription.tog = block.timestamp;
        }
            
        return (err);
    }

    function subscriptionGrant(
        bytes32         a_mkt_subscription,         //  marketplace address of the subscription
        string memory   a_owner_proxy_secret        //  proxy secret of the product referenced by the subscription
    ) public returns (uint err)
    {
        err = subscriptionStatusSet(a_mkt_subscription,a_owner_proxy_secret,STATUS_GRANTED);
        if (err != ERR_OK_NOLOG)
        {
            //  emit the log only if the err is not ERR_OK_NOLOG (optimization)
            emit LogSubscriptionGranted(address(this),a_mkt_subscription,bytes32(err));
        }
        else
        {
            err = ERR_OK;
        }
        
        return(err);
    }


    function subscriptionRevoke(
        bytes32         a_mkt_subscription,         //  marketplace address of the subscription
        string memory   a_owner_proxy_secret        //  proxy secret of the product referenced by the subscription
    ) public returns (uint err)
    {
        err = subscriptionStatusSet(a_mkt_subscription,a_owner_proxy_secret,STATUS_REVOKED);
        if (err != ERR_OK_NOLOG)
        {
            emit LogSubscriptionRevoked(address(this),a_mkt_subscription,bytes32(err));
        }
        else
        {
            err = ERR_OK;
        }
        return(err);
    }


}






