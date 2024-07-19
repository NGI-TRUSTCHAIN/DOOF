//   SPDX-License-Identifier: Apache-2.0
//   © Copyright Ecosteer 2024

//   ver:    1.0
//   date:   03/06/2024
//   author: gabriele-sankalaite

"use strict";

function DOOFwebAPIs(passedOptions) {
  let defaultOptions = {
    client: undefined,
    mainTopic: undefined,
    nginxHost: undefined,
    nginxPort: undefined,
    brokerHost: undefined,
    brokerPort: 8084, // Default port for MQTT over WSS
    tls: undefined,
    protocol: undefined,
    cipherPool: [],
    internalCiphers: [{ id: 2, cipher: "none", mode: "" }], // List of possible ciphers that can be used by DOOF Web APIS
    matchedCiphers: [],
    selectedCipher: undefined,
    authType: undefined,
    auth: undefined,
    supportedAuth: ["jwt", "none"], // List of possible authentication methods that can be used by DOOF Web APIS
    thisSession: undefined,
    authToken: undefined,
    mleSetUp: false,
  };

  const eventsJSON = events();

  const eventHandlers = {
    dop_products_list: { type: "dop_products_list", fun: null },
    dop_subscription_grant: { type: "dop_subscription_grant", fun: null },
    dop_subscription_revoke: { type: "dop_subscription_revoke", fun: null },
    dop_product_subscriptions: { type: "dop_product_subscriptions", fun: null },
    dop_subscription_info: { type: "dop_subscription_info", fun: null },
    dop_product_create: { type: "dop_product_create", fun: null },
    dop_sub_configuration: { type: "dop_sub_configuration", fun: null },
    dop_pub_configuration: { type: "dop_pub_configuration", fun: null },
    dop_account_info: { type: "dop_account_info", fun: null },
    dop_enable_identity: { type: "dop_enable_identity", fun: null },
    dop_client_ready: { type: "dop_client_ready", fun: null },
    dop_cipher_suite_selection: {
      type: "dop_cipher_suite_selection",
      fun: null,
    },
    dop_purpose_create: { type: "dop_purpose_create", fun: null },
    dop_purpose_list: { type: "dop_purpose_list", fun: null },
    dop_product_subscribe: { type: "dop_product_subscribe", fun: null },
    dop_product_unsubscribe: { type: "dop_product_unsubscribe", fun: null },
    dop_recipient_set: { type: "dop_recipient_set", fun: null },
    rif_advertisement_create: { type: "rif_advertisement_create", fun: null },
    rif_actionable_products: { type: "rif_actionable_products", fun: null },
    rif_advertisement_list: { type: "rif_advertisement_list", fun: null },
    rif_advertisement_interest: {
      type: "rif_advertisement_interest",
      fun: null,
    },
    rif_private_message_send: { type: "rif_private_message_send", fun: null },
    rif_private_message_list: { type: "rif_private_message_list", fun: null },
    rif_news_list: { type: "rif_news_list", fun: null },
    error: { type: "error", fun: null },
    log: { type: "log", fun: null },
    other: { type: "other", fun: null },
  };

  const ERROR_CODES = {
    MISSING_OPTIONS: 11900,
    MISSING_BROKER_HOST: 11901,
    MISSING_BROKER_PORT: 11902,
    MISSING_NGINX_HOST: 11903,
    MISSING_NGINX_PORT: 11904,
    MISSING_MLE_CIPHER: 11905,
    MISSING_AUTH_TYPE: 11906,
    MISSING_AUTH_TOKEN: 11907,
  };

  const DEFAULT_MAIN_TOPIC = "events/";

  let confOk = false;
  let onMessageCallback = null;
  let retryCount = 0;
  let isFirstConnection = true;
  let isBrokerConnected = false;
  let isSessionStarted = false;

  let errArray = [];

  if (!passedOptions) {
    errArray.push(ERROR_CODES.MISSING_OPTIONS);
  }

  if (!passedOptions.brokerHost) {
    errArray.push(ERROR_CODES.MISSING_BROKER_HOST);
  } else {
    defaultOptions.brokerHost = passedOptions.brokerHost;
  }

  if (!passedOptions.brokerPort) {
    errArray.push(ERROR_CODES.MISSING_BROKER_PORT);
  } else {
    defaultOptions.brokerPort = passedOptions.brokerPort;
  }

  defaultOptions.mainTopic = passedOptions.brokerTopic
    ? passedOptions.brokerTopic + "/"
    : DEFAULT_MAIN_TOPIC;

  if (!passedOptions.nginxHost) {
    errArray.push(ERROR_CODES.MISSING_NGINX_HOST);
  } else {
    defaultOptions.nginxHost = passedOptions.nginxHost;
  }

  if (!passedOptions.nginxPort) {
    errArray.push(ERROR_CODES.MISSING_NGINX_PORT);
  } else {
    defaultOptions.nginxPort = passedOptions.nginxPort;
  }

  defaultOptions.tls = !!passedOptions.tls;
  defaultOptions.protocol = passedOptions.tls ? "https" : "http";

  if (!passedOptions.mleCipher) {
    errArray.push(ERROR_CODES.MISSING_MLE_CIPHER);
  }

  if (!passedOptions.authType) {
    errArray.push(ERROR_CODES.MISSING_AUTH_TYPE);
  }

  if (passedOptions.authToken === undefined) {
    errArray.push(ERROR_CODES.MISSING_AUTH_TOKEN);
  }

  if (errArray.length > 0) {
    errArray.forEach((errorCode) =>
      console.log("Configuration value error: ", errorCode)
    );
    confOk = false;
  } else {
    console.log("Configuration values are correct");
    const mleP = setMLEPref(passedOptions.mleCipher);
    const authP = setAuthPref(passedOptions.authType, passedOptions.authToken);
    confOk = mleP && authP;
  }

  function status() {
    return confOk;
  }

  async function connectBroker() {
    if (!confOk) {
      return 1;
    }

    const randomNr = Math.random();
    const currentTime = new Date();
    const clientID = "CLID_" + currentTime.getTime() * randomNr;

    // Create a MQTT client instance
    defaultOptions.client = new Paho.Client(
      defaultOptions.brokerHost,
      Number(defaultOptions.brokerPort),
      clientID
    );

    // Set callback handlers
    defaultOptions.client.onConnectionLost = async (responseObject) => {
      if (responseObject.errorCode !== 0) {
        console.log("onConnectionLost:" + responseObject.errorMessage);
        while (retryCount < 5) {
          await new Promise((resolve) => setTimeout(resolve, 10000)); // Delay before reconnect
          retryCount++;
          try {
            await connectBroker();
            if (!isFirstConnection) {
              subscribeToBroker(defaultOptions.thisSession);
            }
            return;
          } catch (error) {
            console.log("Reconnection attempt failed:", error);
            if (retryCount >= 5) {
              console.log("Max reconnection attempts reached, giving up.");
              break;
            }
          }
        }
      }
    };

    defaultOptions.client.onMessageArrived = onMessage;

    await new Promise((resolve, reject) => {
      defaultOptions.client.connect({
        useSSL: defaultOptions.tls,
        onSuccess: () => {
          console.log("onConnect");
          if (isFirstConnection) {
            isFirstConnection = false; // Mark not as a first connection for future attempts
          }
          retryCount = 0; // Reset retry count upon successful connection
          isBrokerConnected = true;

          handlePendingActions();
          resolve(0);
        },
        onFailure: (responseObject) => {
          console.log("onFailure:" + JSON.stringify(responseObject));
          reject(1);
        },
      });
    });
    return 0;
  }

  function setMLEPref(wantedCiphers) {
    // Check whether wanted ciphers (in the application logic) and
    // internal ciphers match
    try {
      defaultOptions.matchedCiphers = [];
      wantedCiphers.forEach((wantedCipher) => {
        const match = defaultOptions.internalCiphers.find(
          (internalCipher) =>
            wantedCipher.id === internalCipher.id &&
            wantedCipher.cipher === internalCipher.cipher &&
            wantedCipher.mode === internalCipher.mode
        );

        if (match) {
          defaultOptions.matchedCiphers.push(match);
        }
      });

      return defaultOptions.matchedCiphers.length > 0;
    } catch (error) {
      console.error("An error occurred while setting MLE preferences:", error);
      return false;
    }
  }

  function setAuthPref(type, auth) {
    // Check if auth type is supported
    if (defaultOptions.supportedAuth.includes(type)) {
      console.log("Authentication type is supported.");
      defaultOptions.authType = type;
      defaultOptions.auth = auth;
      return true;
    } else {
      console.error(
        "Error: Authentication type is not supported by DOOF Web APIs"
      );
      return false;
    }
  }

  function subscribeToBroker(session) {
    let topicToSubscribe = defaultOptions.mainTopic + session;
    console.log("Topic to subscribe to: ", topicToSubscribe);
    defaultOptions.client.subscribe(topicToSubscribe);
    return;
  }

  function handlePendingActions() {
    if (isBrokerConnected && isSessionStarted) {
      subscribeToBroker(defaultOptions.thisSession);
      dop_client_ready();
    }
  }

  function onMessage(message) {
    try {
      const msgJSON = JSON.parse(message.payloadString);
      let processedMessage = msgJSON;

      if (onMessageCallback) {
        const messageObj = {
          topic: message.destinationName,
          qos: message.qos,
          timestamp: Date.now(),
          message: processedMessage,
        };
        onMessageCallback(messageObj);
      }

      let handlerFun = selectListener(processedMessage.event);
      if (handlerFun != null) {
        handlerFun(processedMessage);
      } else {
        console.error(
          `The handler function for ${processedMessage.event} was not defined - please set the handler function`
        );
      }
    } catch (error) {
      console.error("An error occurred while processing the message:", error);
    }
  }

  function setMessageHandler(callback) {
    onMessageCallback = callback;
  }

  function addEventListener(handler_type, handler_fun) {
    for (let event_type in eventHandlers) {
      let handler_entry = eventHandlers[event_type];
      if (handler_entry && handler_entry.type === handler_type) {
        console.log("Handler assigned to:", handler_type);
        handler_entry.fun = handler_fun;
        break;
      }
    }
  }

  function selectListener(event_type) {
    if (event_type in eventHandlers) {
      return eventHandlers[event_type].fun;
    } else if ("other" in eventHandlers) {
      return eventHandlers["other"].fun;
    } else {
      return null;
    }
  }

  async function sendEvent(event, isAuthEvent = false) {
    // Determine the URL based on whether it's an auth event
    const endpoint = isAuthEvent ? "/dop/sysadmin" : "/dop/imperatives";
    const url = `${defaultOptions.protocol}://${defaultOptions.nginxHost}:${defaultOptions.nginxPort}${endpoint}`;

    // Check if MLE is set up, with an additional condition for non-auth events
    if (
      !defaultOptions.mleSetUp &&
      !isAuthEvent &&
      (!event.event === "dop_cipher_suite_selection" ||
        !event.event === "client_ready")
    ) {
      console.error(
        "MLE has not yet been set up between the client and the DOP backend"
      );
      return { error: 1, result: "MLE setup error" };
    }

    let httpOptions = {
      method: "POST",
      mode: "cors",
      cache: "no-cache",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      redirect: "follow",
      referrerPolicy: "no-referrer",
      body: JSON.stringify(event),
    };
    if (defaultOptions.authType === "jwt") {
      httpOptions.headers.Authorization = `Bearer ${defaultOptions.auth}`;
    }

    try {
      const response = await fetch(url, httpOptions);

      if (response.status === 401) {
        return { error: 401, result: "Unauthorized" };
      }

      if (!response.ok) {
        return { error: response.status, result: response.statusText };
      }

      await response.text();
      return { error: 0, result: event };
    } catch (error) {
      console.error("Error in sendEvent:", error);
      return { error: 1, result: error };
    }
  }

  async function start_session(username) {
    try {
      let headers = {
        "Content-Type": "application/json",
      };

      if (defaultOptions.authType === "jwt") {
        headers.Authorization = `Bearer ${defaultOptions.auth}`;
      }

      const response = await fetch(
        `${defaultOptions.protocol}://${defaultOptions.nginxHost}:${defaultOptions.nginxPort}/dop/startsession`,
        {
          method: "POST",
          headers: headers,
          body: JSON.stringify({
            sub: username,
          }),
        }
      );

      console.log("Requesting session...");

      if (response.status === 401) {
        return { error: 401, result: "Unauthorized" };
      }

      if (!response.ok) {
        return { error: response.status, result: response.statusText };
      }

      const data = await response.json();
      console.log("Received message: ", data);
      defaultOptions.thisSession = data.session;
      defaultOptions.authToken = data.auth_token;

      isSessionStarted = true;
      handlePendingActions();

      return { error: 0, result: data };
    } catch (error) {
      console.log("Error when retrieving session");
      console.error(error);
      return { error: 1, result: error };
    }
  }

  //  Event management helpers
  //  All the APIs have an 'options' property that allows to specify
  //  any non mandatory event.header or event.params property

  function normalizeOptions(options) {
    let opt = { header: {}, params: {} };
    if (!options) return opt;
    opt.header = options.header || opt.header;
    opt.params = options.params || opt.params;
    return opt;
  }

  function copyParams(opt, event) {
    //  opt is an object containing the properties header and params
    //  Event is an object with the property params

    // Initialize event.params if it does not exist
    event.params = event.params || {};

    // Copy the properties from opt.params to event.params
    Object.keys(opt.params).forEach((prop) => {
      event.params[prop] = opt.params[prop];
    });
  }

  ////
  // DOP Domain APIs
  ////

  //  The function name is equal to the event type

  async function dop_cipher_suite_selection(keyBase64) {
    addEventListener(
      "dop_cipher_suite_selection",
      on_dop_cipher_suite_selection
    );

    let csEvent = deepClone(eventsJSON.dop_cipher_suite_selection);

    csEvent.session = defaultOptions.thisSession;
    csEvent.params.auth_token = defaultOptions.authToken;
    csEvent.params.cipher_suite = defaultOptions.selectedCipher;
    csEvent.params.cipher_key = keyBase64;

    console.log("Sending event: ");
    console.log(JSON.stringify(csEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(csEvent);
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function dop_client_ready() {
    addEventListener("dop_client_ready", on_dop_client_ready);

    let clientReadyEvent = deepClone(eventsJSON.dop_client_ready);

    clientReadyEvent.session = defaultOptions.thisSession;
    clientReadyEvent.params.auth_token = defaultOptions.authToken;

    console.log("Sending event: ");
    console.log(JSON.stringify(clientReadyEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(
      clientReadyEvent
    );
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function custom_event(
    session,
    authToken,
    event,
    options = null
  ) {
    let customEvent = {
      session: session,
      event: event,
      task: "",
      params: { auth_token: authToken },
    };

    let opt = normalizeOptions(options);

    // Add custom parameters to customEvent.params
    Object.keys(opt.params).forEach((key) => {
      customEvent.params[key] = opt.params[key];
    });
    customEvent.task = "task" in opt.header ? opt.header.task : null;

    console.log("Sending event: ");
    console.log(JSON.stringify(customEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(customEvent);
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function dop_subscription_info(
    session,
    authToken,
    subscriptionID,
    options = null
  ) {
    let mktShowProfileEvent = deepClone(eventsJSON.dop_subscription_info);

    mktShowProfileEvent.session = session;
    mktShowProfileEvent.params.auth_token = authToken;
    mktShowProfileEvent.params.subscription_id = subscriptionID;

    let opt = normalizeOptions(options);
    mktShowProfileEvent.task = "task" in opt.header ? opt.header.task : null;

    console.log("Sending event: ");
    console.log(JSON.stringify(mktShowProfileEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(
      mktShowProfileEvent
    );
    if (eventErr != 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function dop_account_info(
    session,
    authToken,
    options = null
  ) {
    let purposeListEvent = deepClone(eventsJSON.dop_account_info);

    purposeListEvent.session = session;
    purposeListEvent.params.auth_token = authToken;

    let opt = normalizeOptions(options);
    purposeListEvent.task = "task" in opt.header ? opt.header.task : null;

    console.log("Sending event: ");
    console.log(JSON.stringify(purposeListEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(
      purposeListEvent
    );
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function dop_purpose_list(
    session,
    authToken,
    options = null
  ) {
    let purposeListEvent = deepClone(eventsJSON.dop_purpose_list);

    purposeListEvent.session = session;
    purposeListEvent.params.auth_token = authToken;

    let opt = normalizeOptions(options);
    purposeListEvent.task = "task" in opt.header ? opt.header.task : null;

    console.log("Sending event: ");
    console.log(JSON.stringify(purposeListEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(
      purposeListEvent
    );
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function dop_product_create(
    session,
    authToken,
    label,
    price,
    tariff,
    options = null
  ) {
    let purposeCreateEvent = deepClone(eventsJSON.dop_product_create);

    purposeCreateEvent.session = session;
    purposeCreateEvent.params.auth_token = authToken;

    let opt = normalizeOptions(options);
    purposeCreateEvent.task = "task" in opt.header ? opt.header.task : null;

    purposeCreateEvent.params.label = label;
    purposeCreateEvent.params.price = price;
    purposeCreateEvent.params.period = tariff;

    copyParams(opt, purposeCreateEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(purposeCreateEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(
      purposeCreateEvent
    );
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function dop_purpose_create(
    session,
    authToken,
    label,
    url,
    options = null
  ) {
    let purposeCreateEvent = deepClone(eventsJSON.dop_purpose_create);

    purposeCreateEvent.session = session;
    purposeCreateEvent.params.auth_token = authToken;

    let opt = normalizeOptions(options);
    purposeCreateEvent.task = "task" in opt.header ? opt.header.task : null;

    purposeCreateEvent.params.label = label;
    purposeCreateEvent.params.content = url;

    copyParams(opt, purposeCreateEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(purposeCreateEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(
      purposeCreateEvent
    );
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function dop_products_list(
    session,
    authToken,
    options = null
  ) {
    let productsQueryEvent = deepClone(eventsJSON.dop_products_list);

    productsQueryEvent.session = session;
    productsQueryEvent.params.auth_token = authToken;

    let opt = normalizeOptions(options);
    productsQueryEvent.task = "task" in opt.header ? opt.header.task : null;

    copyParams(opt, productsQueryEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(productsQueryEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(
      productsQueryEvent
    );
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function dop_subscription_grant(
    session,
    authToken,
    subscriptionID,
    options = null
  ) {
    let mktGrantEvent = deepClone(eventsJSON.dop_subscription_grant);

    mktGrantEvent.session = session;
    mktGrantEvent.params.auth_token = authToken;
    mktGrantEvent.params.subscription_id = subscriptionID;

    let opt = normalizeOptions(options);
    mktGrantEvent.task = "task" in opt.header ? opt.header.task : null;

    copyParams(opt, mktGrantEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(mktGrantEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(
      mktGrantEvent
    );
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function dop_subscription_revoke(
    session,
    authToken,
    subscriptionID,
    options = null
  ) {
    let mktRevokeEvent = deepClone(eventsJSON.dop_subscription_revoke);

    mktRevokeEvent.session = session;
    mktRevokeEvent.params.auth_token = authToken;
    mktRevokeEvent.params.subscription_id = subscriptionID;

    let opt = normalizeOptions(options);
    mktRevokeEvent.task = "task" in opt.header ? opt.header.task : null;

    copyParams(opt, mktRevokeEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(mktRevokeEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(
      mktRevokeEvent
    );
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function dop_product_subscribe(
    session,
    authToken,
    productID,
    purposeID,
    preAuthCode,
    options = null
  ) {
    let subscribeEvent = deepClone(eventsJSON.dop_product_subscribe);

    subscribeEvent.session = session;
    subscribeEvent.params.auth_token = authToken;
    subscribeEvent.params.product_id = productID;
    subscribeEvent.params.purpose_id = purposeID;
    subscribeEvent.params.pre_auth_code = preAuthCode;

    let opt = normalizeOptions(options);
    subscribeEvent.task = "task" in opt.header ? opt.header.task : null;

    copyParams(opt, subscribeEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(subscribeEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(
      subscribeEvent
    );
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function dop_product_unsubscribe(
    session,
    authToken,
    productID,
    subscriptionID,
    options = null
  ) {
    let unsubscribeEvent = deepClone(eventsJSON.dop_product_unsubscribe);

    unsubscribeEvent.session = session;
    unsubscribeEvent.params.auth_token = authToken;
    unsubscribeEvent.params.product_id = productID;
    unsubscribeEvent.params.subscription_id = subscriptionID;

    let opt = normalizeOptions(options);
    unsubscribeEvent.task = "task" in opt.header ? opt.header.task : null;

    copyParams(opt, unsubscribeEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(unsubscribeEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(
      unsubscribeEvent
    );
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function dop_sub_configuration(
    session,
    authToken,
    subscriptionID,
    options = null
  ) {
    let mktSubConfigQueryEvent = deepClone(eventsJSON.dop_sub_configuration);

    mktSubConfigQueryEvent.session = session;
    mktSubConfigQueryEvent.params.auth_token = authToken;
    mktSubConfigQueryEvent.params.subscription_id = subscriptionID;

    let opt = normalizeOptions(options);
    mktSubConfigQueryEvent.task = "task" in opt.header ? opt.header.task : null;

    copyParams(opt, mktSubConfigQueryEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(mktSubConfigQueryEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(
      mktSubConfigQueryEvent
    );
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function dop_pub_configuration(
    session,
    authToken,
    productID,
    options = null
  ) {
    let mktPubConfigQueryEvent = deepClone(eventsJSON.dop_pub_configuration);

    mktPubConfigQueryEvent.session = session;
    mktPubConfigQueryEvent.params.auth_token = authToken;
    mktPubConfigQueryEvent.params.product_id = productID;

    let opt = normalizeOptions(options);
    mktPubConfigQueryEvent.task = "task" in opt.header ? opt.header.task : null;

    copyParams(opt, mktPubConfigQueryEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(mktPubConfigQueryEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(
      mktPubConfigQueryEvent
    );
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function dop_product_subscriptions(
    session,
    authToken,
    productID,
    type,
    options = null
  ) {
    let mktProdSubQueryEvent = deepClone(eventsJSON.dop_product_subscriptions);

    mktProdSubQueryEvent.session = session;
    mktProdSubQueryEvent.params.auth_token = authToken;
    mktProdSubQueryEvent.params.product_id = productID;
    mktProdSubQueryEvent.params.type = type;

    let opt = normalizeOptions(options);
    mktProdSubQueryEvent.task = "task" in opt.header ? opt.header.task : null;

    copyParams(opt, mktProdSubQueryEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(mktProdSubQueryEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(
      mktProdSubQueryEvent
    );
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function dop_enable_identity(
    session,
    authToken,
    identity,
    screen_name,
    options = null
  ) {
    let enableIdEvent = deepClone(eventsJSON.dop_enable_identity);

    enableIdEvent.session = session;
    enableIdEvent.params.auth_token = authToken;
    enableIdEvent.params.subject = identity;
    enableIdEvent.params.screen_name = screen_name;

    let opt = normalizeOptions(options);
    enableIdEvent.task = "task" in opt.header ? opt.header.task : null;

    copyParams(opt, enableIdEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(enableIdEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(
      enableIdEvent,
      true
    );
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function dop_recipient_set(
    session,
    authToken,
    subject,
    recipient,
    options = null
  ) {
    let recSetEvent = deepClone(eventsJSON.dop_recipient_set);

    recSetEvent.session = session;
    recSetEvent.params.auth_token = authToken;
    recSetEvent.params.subject = subject;
    recSetEvent.params.recipient = recipient;

    let opt = normalizeOptions(options);
    recSetEvent.task = "task" in opt.header ? opt.header.task : null;

    copyParams(opt, recSetEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(recSetEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(
      recSetEvent,
      true
    );
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  ////
  //    RIF Domain APIs
  ////
  async function rif_advertisement_create(
    session,
    authToken,
    secret,
    description,
    purpose_id,
    recipient_ads_id,
    options = null
  ) {
    let thisEvent = deepClone(eventsJSON.rif_advertisement_create);

    thisEvent.session = session;
    thisEvent.params.auth_token = authToken;
    thisEvent.params.secret = secret;
    thisEvent.params.description = description;
    thisEvent.params.purpose_id = purpose_id;
    thisEvent.params.recipient_ads_id = recipient_ads_id;

    let opt = normalizeOptions(options);
    thisEvent.task = "task" in opt.header ? opt.header.task : null;

    copyParams(opt, thisEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(thisEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(thisEvent);
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function rif_advertisement_interest(
    session,
    authToken,
    accept,
    ads_id,
    product_id,
    purpose_id,
    options = null
  ) {
    let thisEvent = deepClone(eventsJSON.rif_advertisement_interest);

    thisEvent.session = session;
    thisEvent.params.auth_token = authToken;
    thisEvent.params.accept = accept;
    thisEvent.params.ads_id = ads_id;
    thisEvent.params.product_id = product_id;
    thisEvent.params.purpose_id = purpose_id;

    let opt = normalizeOptions(options);
    thisEvent.task = "task" in opt.header ? opt.header.task : null;

    copyParams(opt, thisEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(thisEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(thisEvent);
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function rif_advertisement_list(
    session,
    authToken,
    filter,
    options = null
  ) {
    let thisEvent = deepClone(eventsJSON.rif_advertisement_list);

    thisEvent.session = session;
    thisEvent.params.auth_token = authToken;
    thisEvent.params.filter = filter;

    let opt = normalizeOptions(options);
    thisEvent.task = "task" in opt.header ? opt.header.task : null;

    copyParams(opt, thisEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(thisEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(thisEvent);
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function rif_actionable_products(
    session,
    authToken,
    ads_id,
    options = null
  ) {
    let thisEvent = deepClone(eventsJSON.rif_actionable_products);

    thisEvent.session = session;
    thisEvent.params.auth_token = authToken;
    thisEvent.params.ads_id = ads_id;

    let opt = normalizeOptions(options);
    thisEvent.task = "task" in opt.header ? opt.header.task : null;

    copyParams(opt, thisEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(thisEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(thisEvent);
    if (eventErr != 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function rif_private_message_send(
    session,
    authToken,
    secret,
    subscription_id,
    message,
    options = null
  ) {
    let thisEvent = deepClone(eventsJSON.rif_private_message_send);

    thisEvent.session = session;
    thisEvent.params.auth_token = authToken;
    thisEvent.params.secret = secret;
    thisEvent.params.subscription_id = subscription_id;
    thisEvent.params.message = message;

    let opt = normalizeOptions(options);
    thisEvent.task = "task" in opt.header ? opt.header.task : null;

    copyParams(opt, thisEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(thisEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(thisEvent);
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function rif_private_message_list(
    session,
    authToken,
    options = null
  ) {
    let thisEvent = deepClone(eventsJSON.rif_private_message_list);

    thisEvent.session = session;
    thisEvent.params.auth_token = authToken;

    let opt = normalizeOptions(options);
    thisEvent.task = "task" in opt.header ? opt.header.task : null;

    copyParams(opt, thisEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(thisEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(thisEvent);
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  async function rif_news_list(
    session,
    authToken,
    options = null
  ) {
    let thisEvent = deepClone(eventsJSON.rif_news_list);

    thisEvent.session = session;
    thisEvent.params.auth_token = authToken;

    let opt = normalizeOptions(options);
    thisEvent.task = "task" in opt.header ? opt.header.task : null;

    copyParams(opt, thisEvent);

    console.log("Sending event: ");
    console.log(JSON.stringify(thisEvent));

    const { error: eventErr, result: eventRes } = await sendEvent(thisEvent);
    if (eventErr !== 0) {
      console.log("Error when posting event: ", eventRes);
      return { error: eventErr, result: eventRes };
    } else {
      console.log("The event was posted successfully: ", eventRes);
      return { error: eventErr, result: eventRes };
    }
  }

  ////
  // Internal message handler functions
  ////

  async function on_dop_client_ready(message) {
    if (message.params && message.params.cipher_suites) {
      const cipherSuites = message.params.cipher_suites;
      if (cipherSuites.length > 0) {
        defaultOptions.cipherPool = cipherSuites;
        let selectedCipher = await populateArrays();
        if (selectedCipher) {
          let keyBase64 = "";
          if (selectedCipher.name.toLowerCase() === "none") {
            console.log("None cipher was selected - MLE will not be used");
            defaultOptions.selectedCipher = selectedCipher;
            await dop_cipher_suite_selection(keyBase64);
          }
        } else {
          console.error(
            `Selected application layer cipher does not correspond to any cipher supported by DOP Web APIs.\nSupported ciphers are ${JSON.stringify(
              defaultOptions.internalCiphers
            )}`
          );
        }
      }
    } else {
      console.error("Message params or cipher_suites are missing.");
    }
  }

  async function on_dop_cipher_suite_selection() {
    defaultOptions.mleSetUp = true;
  }

  async function populateArrays() {
    let matchedCiphersWorker = [];
    try {
      for (let matchedCipher of defaultOptions.matchedCiphers) {
        for (let poolItem of defaultOptions.cipherPool) {
          if (
            matchedCipher.cipher.toLowerCase() ===
            poolItem.name.toLowerCase() &&
            matchedCipher.mode.toLowerCase() === poolItem.mode.toLowerCase()
          ) {
            matchedCiphersWorker.push(poolItem);
          }
        }
      }

      if (matchedCiphersWorker.length != 0) {
        // Select a random cipher from the matched ciphers
        const randomIndex = Math.floor(
          Math.random() * matchedCiphersWorker.length
        );
        const selectedCipher = matchedCiphersWorker[randomIndex];
        return selectedCipher;
      } else {
        return null;
      }
    } catch (error) {
      return null;
    }
  }

  // Clone each event to manipulate only the clone and not the structure itself
  const deepClone = (obj) => JSON.parse(JSON.stringify(obj));

  return {
    status,
    connectBroker,
    subscribeToBroker,
    onMessage,
    setMessageHandler,
    addEventListener,
    selectListener,
    dopGatewayHost: defaultOptions.dopGatewayHost,
    dopGatewayPort: defaultOptions.dopGatewayPort,
    brokerHost: defaultOptions.brokerHost,
    brokerPort: defaultOptions.brokerPort,
    start_session,
    dop_subscription_info,
    dop_product_create,
    dop_product_subscribe,
    dop_product_unsubscribe,
    dop_sub_configuration,
    dop_pub_configuration,
    dop_product_subscriptions,
    dop_products_list,
    dop_subscription_grant,
    dop_subscription_revoke,
    dop_enable_identity,
    dop_account_info,
    dop_purpose_create,
    dop_purpose_list,
    dop_recipient_set,
    custom_event,
    rif_advertisement_create,
    rif_actionable_products,
    rif_advertisement_list,
    rif_advertisement_interest,
    rif_private_message_send,
    rif_private_message_list,
    rif_news_list,
  };
}
