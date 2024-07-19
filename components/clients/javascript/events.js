//   SPDX-License-Identifier: Apache-2.0
//   © Copyright Ecosteer 2024

//   ver:    1.0
//   date:   03/06/2024
//   author: gabriele-sankalaite

function events() {

  let dop_account_info = {
    session: "",
    task: "",
    event: "dop_account_info",
    params: {
      auth_token: "",
    },
  };

  let dop_cipher_suite_selection = {
    session: "",
    task: "",
    event: "dop_cipher_suite_selection",
    params: {
      auth_token: "",
      cipher_suite: { name: "", mode: "", keylength: "" },
      cipher_key: "",
    },
  };

  let dop_subscription_grant = {
    session: "",
    task: "",
    event: "dop_subscription_grant",
    params: {
      auth_token: "",
      subscription_id: "",
    },
  };

  let dop_products_list = {
    session: "",
    task: "",
    event: "dop_products_list",
    params: {
      set_range: { from: 0, to: 20 },
      filter: {},
      auth_token: "",
    },
  };

  let dop_pub_configuration = {
    session: "",
    task: "",
    event: "dop_pub_configuration",
    params: {
      auth_token: "",
      product_id: "",
    },
  };

  let dop_sub_configuration = {
    session: "",
    task: "",
    event: "dop_sub_configuration",
    params: {
      auth_token: "",
      subscription_id: "",
    },
  };

  let dop_subscription_revoke = {
    session: "",
    task: "",
    event: "dop_subscription_revoke",
    params: { auth_token: "", subscription_id: "" },
  };

  let dop_product_create = {
    session: "",
    task: "",
    event: "dop_product_create",
    params: {
      label: "",
      price: 0,
      period: 0,
    },
  };

  let dop_product_subscribe = {
    session: "",
    task: "",
    event: "dop_product_subscribe",
    params: { auth_token: "", product_id: "", purpose_id: "", pre_auth_code: "" },
  };

  let dop_product_unsubscribe = {
    session: "",
    task: "",
    event: "dop_product_unsubscribe",
    params: { auth_token: "", product_id: "", subscription_id: "" },
  };

  let dop_client_ready = {
    session: "",
    task: "",
    event: "dop_client_ready",
    params: { auth_token: "" },
  };

  let dop_enable_identity = {
    session: "",
    task: "",
    event: "dop_enable_identity",
    params: { auth_token: "", subject: "", screen_name: "" },
  };

  let dop_product_subscriptions = {
    session: "",
    task: "",
    event: "dop_product_subscriptions",
    params: { auth_token: "", product_id: "", type: "" },
  };

  let dop_purpose_create = {
    session: "",
    task: "",
    event: "dop_purpose_create",
    params: { auth_token: "", label: "", content: "" },
  };

  let dop_purpose_list = {
    session: "",
    task: "",
    event: "dop_purpose_list",
    params: { auth_token: "" },
  };

  let dop_subscription_info = {
    session: "",
    task: "",
    event: "dop_subscription_info",
    params: { auth_token: "", subscription_id: "" },
  };

  let dop_recipient_set = {
    session: "",
    task: "",
    event: "dop_recipient_set",
    params: { auth_token: "", subject: "", recipient: "" },
  };

  let rif_advertisement_create = {
    session: "",
    task: "",
    event: "rif_advertisement_create",
    params: { auth_token: "", secret: "", description: "", purpose_id: "", recipient_ads_id: "" },
  };

  let rif_advertisement_interest = {
    session: "",
    task: "",
    event: "rif_advertisement_interest",
    params: { auth_token: "", accept: false, ads_id: "", product_id: "", purpose_id: "" },
  };

  let rif_advertisement_list = {
    session: "",
    task: "",
    event: "rif_advertisement_list",
    params: { auth_token: "", filter: "other" },
  };

  let rif_actionable_products = {
    session: "",
    task: "",
    event: "rif_actionable_products",
    params: { auth_token: "", ads_id: "" },
  };

  let rif_private_message_send = {
    session: "",
    task: "",
    event: "rif_private_message_send",
    params: { auth_token: "", secret: "", subscription_id: "", message: "" },
  };

  let rif_private_message_list = {
    session: "",
    task: "",
    event: "rif_private_message_list",
    params: { auth_token: "" },
  };

  let rif_news_list = {
    session: "",
    task: "",
    event: "rif_news_list",
    params: { auth_token: "" },
  };


  let custom_event = {
    session: "",
    task: "",
    event: "",
    params: { auth_token: "" },
  };

  return {
    dop_product_subscribe: dop_product_subscribe,
    dop_product_unsubscribe: dop_product_unsubscribe,
    dop_cipher_suite_selection: dop_cipher_suite_selection,
    dop_client_ready: dop_client_ready,
    dop_enable_identity: dop_enable_identity,
    dop_account_info: dop_account_info,
    dop_product_subscriptions: dop_product_subscriptions,
    dop_purpose_create: dop_purpose_create,
    dop_purpose_list: dop_purpose_list,
    dop_subscription_info: dop_subscription_info,
    dop_subscription_grant: dop_subscription_grant,
    dop_products_list: dop_products_list,
    dop_pub_configuration: dop_pub_configuration,
    dop_sub_configuration: dop_sub_configuration,
    dop_subscription_revoke: dop_subscription_revoke,
    dop_product_create: dop_product_create,
    dop_recipient_set: dop_recipient_set,
    rif_advertisement_create: rif_advertisement_create,
    rif_actionable_products: rif_actionable_products,
    rif_advertisement_list: rif_advertisement_list,
    rif_advertisement_interest: rif_advertisement_interest,
    rif_private_message_send: rif_private_message_send,
    rif_private_message_list: rif_private_message_list,
    rif_news_list: rif_news_list,
    custom_event: custom_event
  };
}
