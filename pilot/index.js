//   SPDX-License-Identifier: Apache-2.0
//   © Copyright Ecosteer 2024

//   ver:    1.0
//   date:   28/06/2024
//   author: gabriele-sankalaite

"use strict";

const TASK_NOT_GRANTED_SUBSCRIPTIONS = 9;
const TASK_GRANTED_SUBSCRIPTIONS = 10;
const TASK_PRODUCTS_OTHER = 11;
const TASK_PRODUCTS_PUBLISHED = 12;
const TASK_PRODUCT_DETAILS_PUB = 14;
const TASK_ACCOUNT_INFO_CUSTOM = 26;
const TASK_PRODUCT_DETAILS_OTHER = 34;
const TASK_ACTIONABLE_PRODUCTS_ACCEPT = 36;
const TASK_ACTIONABLE_PRODUCTS_REJECT = 35;
const TASK_PRODUCT_DETAILS_INFO = 33;

let DOOF;
let currentUser;
let username;
let ownerUrl;
let protocol;
let g_selection = null;
let g_active = null;
let publishedProds;

class UserState {
  constructor(session) {
    this.email = undefined;
    this.accountID = undefined;
    this.session = session;
    this.authToken = undefined;
    this.isActiveSession = false;
  }

  setAuthToken(authToken) {
    this.authToken = authToken;
  }

  setAccountID(accountID) {
    this.accountID = accountID;
  }
}

// Initialise new user state
function newUserState(session) {
  currentUser = new UserState(session);
}

// Connect to broker and DOOF Gateway upon loading the window
document.addEventListener("DOMContentLoaded", function () {
  console.log("Session storage: ", sessionStorage);
  //  The configuration file to be used by the client is provided
  //  by the owner of the Data Exchange application
  app_show("welcomePage");
  $.getJSON("index_config.json", function (config) {
    const isHttps = window.location.protocol === "https:";
    const protocol = isHttps ? "https" : "http";
    const tls = isHttps;

    let authType;
    let authToken;
    if (!config.authType) {
      console.error(
        "Missing authentication type - please adjust your configuration file"
      );
      return;
    }
    if (config.authType === "jwt") {
      const jwt = sessionStorage.getItem("jwt");
      const usn = sessionStorage.getItem("username");
      if (jwt && usn) {
        authType = config.authType;
        authToken = jwt;
        username = usn;
        if (config.ownerAppHost && config.ownerAppPort) {
          ownerUrl = `${protocol}://${config.ownerAppHost}:${config.ownerAppPort}/apps/owner/owner_app.html?sid=`;
        }
      } else {
        alert("Authentication needed");
        window.location.href = "login.html";
        return;
      }
    } else if (config.authType === "none") {
      const usn = sessionStorage.getItem("username");
      if (usn) {
        authType = config.authType;
        authToken = null;
        username = usn;
        if (config.ownerAppHost && config.ownerAppPort) {
          ownerUrl = `${protocol}://${config.ownerAppHost}:${config.ownerAppPort}/apps/owner/owner_app.html?sid=`;
        }
      } else {
        alert("Authentication needed");
        window.location.href = "login.html";
        return;
      }
    } else {
      console.error(config.authType, " not supported by this application");
      return;
    }

    const options = {
      brokerHost: config.brokerHost,
      brokerPort: config.brokerPort,
      brokerTopic: config.brokerTopic,
      nginxHost: config.nginxHost,
      nginxPort: config.nginxPort,
      tls: tls,
      mleCipher: config.mleCipher,
      authType: authType,
      authToken: authToken,
    };
    connectToDOOF(options);
  });
});

async function connectToDOOF(options) {
  DOOF = DOOFwebAPIs(options);
  //  Install the event handler for the events that will be presented
  //  asynchronously through the DOOF broker
  setEventListeners();
  DOOF.setMessageHandler(handleEvents);

  try {
    const result = await DOOF.connectBroker();
    if (result === 0) {
      console.log("Successfully connected to the broker");
    } else {
      console.log("Connection to the broker failed");
    }
  } catch (error) {
    console.log("An error occurred while connecting to the broker");
    console.log(error);
  }

  // Start session
  const { error: sessEventErr, result: sessEventRes } = await DOOF.start_session(
    username
  );
  if (sessEventErr === 0) {
    let session = sessEventRes.session;
    newUserState(session);
    currentUser.email = username;
    currentUser.setAuthToken(sessEventRes.auth_token);
    // Handle account info
    handleAccountInfo();
    // Handle billboard announcements
    handleRIFAdvertisementList();
    app_show("billboardPage");
  } else if (sessEventErr === 401) {
    alert("Unauthorized");
    window.location.href = "login.html";
    return;
  }
}

/////
///// API HANDLER FUNCTIONS
/////

// Handle logout
function handleLogout() {
  sessionStorage.removeItem("username");
  sessionStorage.removeItem("jwt");

  window.location.href = "login.html";
  return;
}

// Handle custom event
async function handleCustomEvent(event, options = null) {
  const { error: customErr, result: customRes } = await DOOF.custom_event(
    currentUser.session,
    currentUser.authToken,
    event,
    options
  );
  if (customErr != 0) {
    alert("Custom request failed");
    return;
  }
}

///
/// RIF IMPERATIVES HANDLERS
///

async function handleRIFAdvertisementList() {
  const { error: eventErr, result: eventRes } =
    await DOOF.rif_advertisement_list(
      currentUser.session,
      currentUser.authToken,
      "other"
    );
  if (eventErr != 0) {
    alert("RIF advertisement list failed");
    return;
  }
}

async function handleRIFActionableProducts(task, ads_id) {
  const opt = {
    header: { task: task },
    params: {},
  };

  const { error: eventErr, result: eventRes } =
    await DOOF.rif_actionable_products(
      currentUser.session,
      currentUser.authToken,
      ads_id,
      opt
    );

  if (eventErr != 0) {
    alert("RIF actionable products failed");
    return;
  }
}

async function handleRIFActionableProductsAccept(ads_id) {
  handleRIFActionableProducts(TASK_ACTIONABLE_PRODUCTS_ACCEPT, ads_id);
}

async function handleRIFActionableProductsReject(ads_id) {
  handleRIFActionableProducts(TASK_ACTIONABLE_PRODUCTS_REJECT, ads_id);
}

async function handlePrivateMsgListQuery() {
  const { error: eventErr, result: eventRes } =
    await DOOF.rif_private_message_list(
      currentUser.session,
      currentUser.authToken
    );
  if (eventErr != 0) {
    alert("Private message list request failed");
    return;
  }
}

async function handleRIFNotificationList() {
  const { error: eventErr, result: eventRes } = await DOOF.rif_news_list(
    currentUser.session,
    currentUser.authToken
  );
  if (eventErr != 0) {
    alert("Notification list request failed");
    return;
  }
}

async function handleRIFAdvertisementInterest(
  action,
  ads_id,
  prods,
  purpose_id
) {
  for (const product of prods) {
    try {
      const { error: eventErr, result: eventRes } =
        await DOOF.rif_advertisement_interest(
          currentUser.session,
          currentUser.authToken,
          action,
          ads_id,
          product,
          purpose_id
        );

      if (eventErr != 0) {
        alert("RIF advertisement interest request failed");
        return;
      }
    } catch (err) {
      alert("RIF advertisement interest request failed");
      return;
    }
  }
}

///
/// DOP IMPERATIVES HANDLERS
///

async function handleAccountInfo(task = TASK_ACCOUNT_INFO_CUSTOM) {
  const opt = {
    header: { task: task },
    params: {},
  };

  const { error: accInfoErr, result: accInfoRes } = await DOOF.dop_account_info(
    currentUser.session,
    currentUser.authToken,
    opt
  );
  if (accInfoErr != 0) {
    alert("Account info request failed");
    return;
  }
}

async function handleProductsQuery(options) {
  const { error: listProductsErr, result: listProductsRes } =
    await DOOF.dop_products_list(
      currentUser.session,
      currentUser.authToken,
      options
    );
  if (listProductsErr != 0) {
    alert("Products request failed");
    return;
  }
}

async function handlePublishedProductsQuery() {
  const opt = {
    header: { task: TASK_PRODUCTS_PUBLISHED },
    params: { type: "published", set_range: { from: 0, to: 1000 }, filter: {} },
  };
  await handleProductsQuery(opt);
}

async function handleOtherProductsQuery() {
  const opt = {
    header: { task: TASK_PRODUCTS_OTHER },
    params: { type: "other", set_range: { from: 0, to: 1000 }, filter: {} },
  };
  await handleProductsQuery(opt);
}

async function pub_handleViewSubscriptionsGranted(
  productID = g_selection.pid,
  type = "all",
  task = TASK_GRANTED_SUBSCRIPTIONS
) {
  handleViewSubscriptions(type, task, productID);
}

async function pub_handleViewSubscriptionsNotGranted(
  productID = g_selection.pid,
  type = "all",
  task = TASK_NOT_GRANTED_SUBSCRIPTIONS
) {
  handleViewSubscriptions(type, task, productID);
}

async function handleViewSubscriptions(type, task, productID) {
  const { error: subsErr, result: subsRes } =
    await DOOF.dop_product_subscriptions(
      currentUser.session,
      currentUser.authToken,
      productID,
      type,
      {
        header: { task: task },
        params: {},
      }
    );
  if (subsErr != 0) {
    alert("Product subscriptions request failed");
    return;
  }
}

async function handleGetDetails(options) {
  const { error: pubProdErr, result: pubProdRes } = await DOOF.dop_products_list(
    currentUser.session,
    currentUser.authToken,
    options
  );
  if (pubProdErr != 0) {
    alert("Product details request failed");
    return;
  }
}

async function pub_handleGetDetails(productID) {
  const opt = {
    header: { task: TASK_PRODUCT_DETAILS_PUB },
    params: {
      type: "published",
      set_range: { from: 0, to: 1000 },
      filter: { id: productID },
    },
  };
  await handleGetDetails(opt);
}

async function other_handleGetDetails(productID) {
  const opt = {
    header: { task: TASK_PRODUCT_DETAILS_OTHER },
    params: {
      type: "other",
      set_range: { from: 0, to: 1000 },
      filter: { id: productID },
    },
  };
  await handleGetDetails(opt);
}

async function info_handleGetDetails(productID) {
  const opt = {
    header: { task: TASK_PRODUCT_DETAILS_INFO },
    params: {
      type: "published",
      set_range: { from: 0, to: 1000 },
      filter: { id: productID },
    },
  };
  await handleGetDetails(opt);
}

async function pub_handleDownloadConf(productID) {
  const { error: pubConfErr, result: pubConfRes } =
    await DOOF.dop_pub_configuration(
      currentUser.session,
      currentUser.authToken,
      productID
    );
  if (pubConfErr != 0) {
    alert("Publisher configuration request failed");
    return;
  }
}

async function handleSubGovernanceAction(subscriptionID, action) {
  if (action.toLowerCase() === "approve") {
    const { error: grantErr, result: grantRes } =
      await DOOF.dop_subscription_grant(
        currentUser.session,
        currentUser.authToken,
        subscriptionID
      );
    if (grantErr != 0) {
      alert("Approve request failed");
      return;
    }
  } else if (action.toLowerCase() === "revoke") {
    const { error: revokeErr, result: revokeRes } =
      await DOOF.dop_subscription_revoke(
        currentUser.session,
        currentUser.authToken,
        subscriptionID
      );
    if (revokeErr != 0) {
      alert("Revoke request failed");
      return;
    }
  }
}

async function handleChangeScreenName(newScreenName) {
  const opt = {
    header: {},
    params: { new_screen_name: newScreenName },
  };
  await handleCustomEvent("dex_change_screen", opt);
}

async function handleChangePassword(currentPwd, newPwd) {
  const opt = {
    header: {},
    params: { old_password: currentPwd, new_password: newPwd },
  };
  await handleCustomEvent("dex_change_password", opt);
}

/////
///// HELPER FUNCTIONS
/////

function saveScreenName() {
  const newScreenName = document
    .getElementById("new-screen-input")
    .value.trim();

  // Check if the new screen name is empty
  if (newScreenName === "") {
    alert("Screen name cannot be empty");
    return;
  }

  // Check if the new screen name exceeds the maximum length
  if (newScreenName.length > 30) {
    alert("Screen name cannot exceed 30 characters");
    return;
  }

  // Sanitize the input
  const sanitizedScreenName = sanitizeInput(newScreenName);

  // Check if the sanitized screen name is still not empty after removing harmful characters
  if (sanitizedScreenName === "") {
    alert("Invalid screen name");
    return;
  }

  handleChangeScreenName(sanitizedScreenName);
}

function isPasswordValid(password) {
  // Check length
  if (password.length < 8 || password.length > 30) {
    return false;
  }
  // Check for spaces and non-ASCII characters
  for (let i = 0; i < password.length; i++) {
    const charCode = password.charCodeAt(i);
    if (charCode <= 32 || charCode >= 126) {
      return false;
    }
  }
  return true;
}

function saveNewPassword() {
  const currentPassword = document
    .getElementById("current-pwd-input")
    .value.trim();
  const newPassword = document.getElementById("new-pwd-input").value.trim();
  const confirmPassword = document
    .getElementById("new-pdw-confirm-input")
    .value.trim();

  if (currentPassword === "" || newPassword === "" || confirmPassword === "") {
    alert("All password fields must be filled out.");
    return;
  }

  // Check if new password matches confirm password
  if (newPassword !== confirmPassword) {
    alert("New password and confirm password do not match.");
    return;
  }

  // Validate new password
  if (!isPasswordValid(newPassword)) {
    alert(
      "New password is invalid. It must be 8-30 characters long and contain only ASCII characters without spaces."
    );
    return;
  }

  handleChangePassword(currentPassword, newPassword);
}

// Function to sanitize the input (removing potentially harmful elements)
function sanitizeInput(input) {
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#x27;",
    "/": "&#x2F;",
  };
  const reg = /[&<>"'/]/gi;
  return input.replace(reg, (match) => map[match]);
}

/////
///// FUNCTIONS FOR RENDERING VARIOUS ELEMENTS
/////

function updateUsernameDisplay(username) {
  $(".usernameDisplay").text(username);
  $(".screenDisplay").text(screen);
}

function updateScreenDisplay(screen) {
  $(".screenDisplay").text(screen);
}

async function renderProductsPublished(products) {
  const container = "#productsPage .product-list";
  const template = "#productCardTemplate";

  $(container).empty();

  if (products.length === 0) {
    $("#img-placeholder-asset").removeClass("d-none");
  }

  // Iterate through each product and clone the template
  products.forEach((product) => {
    $("#img-placeholder-asset").addClass("d-none");

    const newProductCard = $(template)
      .clone()
      .removeClass("d-none")
      .removeAttr("id");

    newProductCard.attr("id", "pid_" + product.id);
    newProductCard.find(".productName").text(product.label);
    newProductCard
      .find(".productDate")
      .text(extractDatePart(product.created_at));
    newProductCard
      .find(".subscriptionsText")
      .text(product.no_subscriptions + " Subscriptions");

    const subscriptionsButtonId = "subscriptionsButton_" + product.id;
    const detailsButtonId = "detailsButton_" + product.id;
    newProductCard
      .find(".subscriptionsButton")
      .attr("id", subscriptionsButtonId);
    newProductCard.find(".detailsButton").attr("id", detailsButtonId);

    newProductCard.find("#" + subscriptionsButtonId).on("click", function () {
      pub_handleViewSubscriptionsGranted(product.id);
      g_selection = {
        pid: product.id,
        label: product.label,
        date: extractDatePart(product.created_at),
        side: "published",
      };
    });

    newProductCard.find("#" + detailsButtonId).on("click", function () {
      pub_handleGetDetails(product.id);
    });

    $(container).append(newProductCard);
  });

  app_show("productsPage");
}

async function renderProductsAll(products) {
  const container = "#allProducts .product-list";
  const template = "#productCardTemplateAll";
  const templateElement = $(template);

  $(container).empty();

  // Iterate through each product and clone the template
  products.forEach((product) => {
    const newProductCard = templateElement.clone();

    newProductCard.removeClass("d-none").removeAttr("id");
    newProductCard.attr("id", "pid_" + product.id);
    newProductCard.find(".productNameAll").text(product.label);
    newProductCard
      .find(".productDateAll")
      .text(extractDatePart(product.created_at));

    newProductCard.find(".detailsButtonAll").on("click", function () {
      other_handleGetDetails(product.id);
    });

    $(container).append(newProductCard);
  });

  $("#allProducts").show();
}

function renderGrantRevokeSubscriptions(allSubscriptions, type) {
  const { grantedCount, notGrantedCount } =
    countSubscriptions(allSubscriptions);

  // Update count based on type
  if (type === "granted") {
    $("#grantedApprovedCount").text(grantedCount);
    $("#grantedApprovedCountMobile").text(grantedCount);
    $("#grantedNotApprovedCount").text(notGrantedCount);
    $("#grantedNotApprovedCountMobile").text(notGrantedCount);
    $("#followersGrantedLabel").text(g_selection.label);
    $("#followersGrantedInfo").text(`${g_selection.date}`);
  } else {
    $("#notGrantedApprovedCount").text(grantedCount);
    $("#notGrantedApprovedCountMobile").text(grantedCount);
    $("#notGrantedNotApprovedCount").text(notGrantedCount);
    $("#notGrantedNotApprovedCountMobile").text(notGrantedCount);
    $("#followersNotGrantedLabel").text(g_selection.label);
    $("#followersNotGrantedInfo").text(`${g_selection.date}`);
  }

  const subscriptions = filterByStatus(allSubscriptions, type);
  const containerId =
    type === "granted"
      ? "followersGrantedContainer"
      : "followersNotGrantedContainer";
  const listId =
    type === "granted"
      ? "#grantedSubscriptionsList"
      : "#notGrantedSubscriptionsList";
  const noSubscriptionsId =
    type === "granted"
      ? "#noGrantedSubscriptions"
      : "#noNotGrantedSubscriptions";

  $(listId).empty();

  // Handle owner's subscription separately
  let ownerSubscription = null;
  subscriptions.forEach((subscription, index) => {
    if (subscription.subscriber_id === currentUser.accountID) {
      ownerSubscription = subscription;
      subscriptions.splice(index, 1);
    }
  });

  if (ownerSubscription) {
    const ownerItem = $("#subscriptionOwnerTemplate")
      .clone()
      .removeClass("d-none")
      .removeAttr("id");
    ownerItem
      .find("#ownerRequestDate")
      .text(extractDatePart(ownerSubscription.created_at));
    ownerItem
      .find("#ownerPurposeLink")
      .attr("href", ownerSubscription.purpose_url);
    ownerItem.find("#ownerPurposeLabel").text("Purpose of Usage");

    const ownerStatusIconClass =
      ownerSubscription.status === 1
        ? "bx-check-circle text-success"
        : "bx-x-circle text-danger";
    const actionText = ownerSubscription.status === 1 ? "Revoke" : "Approve";
    const actionButtonClass =
      ownerSubscription.status === 1
        ? "btn-outline-danger"
        : "btn-outline-success";
    const actionIconClass =
      ownerSubscription.status === 1 ? "bx-x" : "bx-check";

    ownerItem.find("#ownerStatusIcon").addClass(ownerStatusIconClass);
    ownerItem
      .find("#ownerActionButton")
      .addClass(actionButtonClass)
      .attr(
        "onclick",
        `handleSubGovernanceAction('${ownerSubscription.subscription_id}', '${actionText}')`
      )
      .attr("id", "BT_" + ownerSubscription.subscription_id);
    ownerItem.find("#ownerActionIcon").addClass(actionIconClass);
    ownerItem.find("#ownerActionText").text(actionText);
    ownerItem
      .find("#ownerDataButton")
      .attr(
        "onclick",
        `window.open('${ownerUrl}${ownerSubscription.subscription_id}', '_blank')`
      );

    $(listId).prepend(ownerItem); // Prepend to ensure it's the first item in the list
  }

  if (subscriptions.length === 0 && !ownerSubscription) {
    console.log("No subscriptions found.");
    $(noSubscriptionsId).removeClass("d-none");
  } else {
    $(noSubscriptionsId).addClass("d-none");

    subscriptions.forEach((subscription) => {
      const newSubscriberItem = $("#subscriptionTemplate")
        .clone()
        .removeClass("d-none")
        .removeAttr("id");
      newSubscriberItem
        .find("#subscriberName")
        .text(subscription.subscriber_screen);
      newSubscriberItem
        .find("#requestDate")
        .text(`Requested on ${extractDatePart(subscription.created_at)}`);
      newSubscriberItem
        .find("#purposeLink")
        .attr("href", subscription.purpose_url);
      newSubscriberItem.find("#purposeLabel").text("Purpose of Usage");

      const statusIconClass =
        subscription.status === 1
          ? "bx-check-circle text-success"
          : "bx-x-circle text-danger";
      const actionText = subscription.status === 1 ? "Revoke" : "Approve";
      const actionButtonClass =
        subscription.status === 1
          ? "btn-outline-danger"
          : "btn-outline-success";
      const actionIconClass = subscription.status === 1 ? "bx-x" : "bx-check";

      newSubscriberItem.find("#statusIcon").addClass(statusIconClass);
      newSubscriberItem
        .find("#actionButton")
        .addClass(actionButtonClass)
        .attr(
          "onclick",
          `handleSubGovernanceAction('${subscription.subscription_id}', '${actionText}')`
        )
        .attr("id", "BT_" + subscription.subscription_id);
      newSubscriberItem.find("#actionIcon").addClass(actionIconClass);
      newSubscriberItem.find("#actionText").text(actionText);

      $(listId).append(newSubscriberItem);
    });
  }

  app_show("followersList");
  app_show(containerId);
}

function renderProductDetails(productInfo, type) {
  const isPub = type === "pub";

  const labelId = isPub ? "#productDetailLabel" : "#productDetailLabelAll";
  const dateLocationId = isPub
    ? "#productDetailDateLocation"
    : "#productDetailDateLocationAll";
  const nameId = isPub ? "#productDetailName" : "#productDetailNameAll";
  const publisherId = isPub
    ? "#productDetailPublisher"
    : "#productDetailPublisherAll";
  const createdAtId = isPub
    ? "#productDetailCreatedAt"
    : "#productDetailCreatedAtAll";

  $(labelId).text(productInfo.label);
  $(dateLocationId).text(`${extractDatePart(productInfo.created_at)}`);
  $(nameId).text(productInfo.label);
  $(publisherId).text(productInfo.publisher);
  $(createdAtId).text(extractDatePart(productInfo.created_at));

  // Attach the onClick event to the configuration button if type is 'pub'
  if (isPub) {
    $("#downloadConfigButton")
      .off("click")
      .on("click", function () {
        pub_handleDownloadConf(productInfo.id);
      });
  }

  // Show the correct product details section
  const detailsPageId = isPub ? "productDetailsPub" : "productDetailsAll";
  app_show(detailsPageId);
}

async function renderBillboardAdvs(ads) {
  const container = "#billboardAdsList";
  const template = "#advNewTemplate";

  $(container).empty();

  if (ads.length === 0) {
    $("#img-placeholder").removeClass("d-none");
  }

  // Iterate through each ad and clone the template
  ads.forEach((ad) => {
    $("#img-placeholder").addClass("d-none");
    const newAdCard = $(template)
      .clone()
      .removeClass("d-none")
      .removeClass("d-sm-none")
      .removeAttr("id");

    newAdCard.attr("id", "adid_" + ad.ads_id);
    newAdCard.data("purpose-id", ad.purpose_id);
    newAdCard
      .find("#advCompanyNameTemplate")
      .attr("id", "advCompanyName_" + ad.ads_id)
      .text(ad.company_name);
    newAdCard
      .find("#advPurposeLinkTemplate")
      .attr("id", "advPurposeLink_" + ad.ads_id)
      .attr("href", ad.purpose_url);
    newAdCard
      .find("#advPurposeLabelTemplate")
      .attr("id", "advPurposeLabel_" + ad.ads_id)
      .text("Purpose of Usage");
    newAdCard
      .find("#advDescriptionTemplate")
      .attr("id", "advDescription_" + ad.ads_id)
      .text(ad.description);
    newAdCard
      .find("#advAdditionalInfoTemplate")
      .attr("id", "advAdditionalInfo_" + ad.ads_id)
      .text(ad.additional_info);

    const acceptAdButtonId = "acceptAdButton_" + ad.ads_id;
    const rejectAdButtonId = "rejectAdButton_" + ad.ads_id;

    newAdCard
      .find("#advAcceptButtonTemplate")
      .attr("id", acceptAdButtonId)
      .off("click")
      .on("click", function () {
        handleRIFActionableProductsAccept(ad.ads_id);
      });

    newAdCard
      .find("#advRejectButtonTemplate")
      .attr("id", rejectAdButtonId)
      .off("click")
      .on("click", function () {
        handleRIFActionableProductsReject(ad.ads_id);
      });

    $(container).append(newAdCard);
  });

  app_show("billboardPage");
}

function renderMultipleProductsModal(ads_id, prods, action) {
  const modalId = action === "accept" ? "#multiple-products-accept" : "#multiple-products-reject";
  const container = action === "accept" ? "#accept-products-list" : "#reject-products-list";
  const actionButtonId = action === "accept" ? "#testEnableButtonAccept" : "#testEnableButtonReject";
  const templateId = "#product-template";

  $(container).empty();
  $(actionButtonId).prop("disabled", true);

  // Generate product cards and append to the container
  prods.forEach((prod, index) => {
    const productCard = $(templateId)
      .clone()
      .removeClass("d-none")
      .removeAttr("id");
    productCard.find(".product-date").text(extractDatePart(prod.created_at));
    productCard
      .find(".product-subscriptions")
      .text(" | " + prod.no_subscriptions + " Subscriptions");
    productCard.find(".product-name").text(prod.label);
    productCard
      .find(".product-checkbox")
      .attr("id", `ex-check-${action}-${index}`)
      .data("prod-id", prod.id);

    $(container).append(productCard);
  });

  // Attach event listener to checkboxes
  $(container)
    .off("change")
    .on("change", ".product-checkbox", function () {
      const anyChecked = $(container).find(".product-checkbox:checked").length > 0;
      $(actionButtonId).prop("disabled", !anyChecked);
    });

  $(actionButtonId)
    .off("click")
    .on("click", function () {
      handleMultipleProductsAction(ads_id, action);
    });

  // Show the modal
  const modalElement = document.querySelector(modalId);
  let modalInstance = bootstrap.Offcanvas.getInstance(modalElement);
  if (!modalInstance) {
    modalInstance = new bootstrap.Offcanvas(modalElement);
  }
  modalInstance.show();

  $(modalElement)
    .off("hide.bs.offcanvas")
    .on("hide.bs.offcanvas", function () {
      $(container).empty();
      $(actionButtonId).prop("disabled", true);
    });
}

function handleMultipleProductsAction(ads_id, action) {
  const modalId = action === "accept" ? "#multiple-products-accept" : "#multiple-products-reject";
  const selectedProducts = $(modalId)
    .find(".product-checkbox:checked")
    .map(function () {
      return $(this).data("prod-id");
    })
    .get();

  const adElement = $("#adid_" + ads_id);
  const purposeId = adElement.data("purpose-id");

  if (action === "accept") {
    multipleProductsAccept(ads_id, selectedProducts, purposeId);
  } else {
    multipleProductsReject(ads_id, selectedProducts, purposeId);
  }

  const modalElement = document.querySelector(modalId);
  const modalInstance = bootstrap.Offcanvas.getInstance(modalElement);
  modalInstance.hide();
}

function multipleProductsAccept(ads_id, selectedProducts, purpose_id) {
  handleRIFAdvertisementInterest(true, ads_id, selectedProducts, purpose_id);
}

function multipleProductsReject(ads_id, selectedProducts, purpose_id) {
  handleRIFAdvertisementInterest(false, ads_id, selectedProducts, purpose_id);
}

async function renderPrivateMsgs(private_msgs) {
  const container = "#messageContainer";
  const template = "#messageTemplate";
  const templateElement = $(template);

  $(container).empty();

  if (private_msgs.length === 0) {
    $("#img-placeholder-msg").removeClass("d-none");
  }

  // Iterate through each private message and clone the template
  private_msgs.forEach((msg) => {
    $("#img-placeholder-msg").addClass("d-none");

    const newMessage = templateElement.clone();

    newMessage.removeClass("d-none");
    newMessage.removeAttr("id");

    if (msg.partner_name && msg.purpose_url) {
      newMessage.find(".companyLabel").text(msg.partner_name);
      newMessage.find(".purposeLabel").text("Purpose of Usage");

      newMessage
        .find(".messageContent")
        .text(
          `${msg.partner_name} has sent you an access token to their service.`
        );
      newMessage.find(".purposeUrl").attr("href", msg.purpose_url);
      newMessage.find(".serviceLink").attr("href", msg.message);
      newMessage
        .find("#goToServiceButton")
        .attr("onclick", `window.open('${msg.message}', '_blank')`);
    } else {
      // Handle the case where any of the fields are null
      newMessage.find(".companyLabel").text("");
      newMessage.find(".purposeLabel").text("");
      newMessage
        .find(".messageContent")
        .text(
          "It seems that this subscription does not exist anymore. You may still access the associated service."
        );
      newMessage.find(".purposeUrl").removeAttr("href");
      newMessage.find(".serviceLink").attr("href", msg.message);
      newMessage
        .find("#goToServiceButton")
        .attr("onclick", `window.open('${msg.message}', '_blank')`);
    }

    $(container).append(newMessage);
  });

  app_show("messagesPage");
}

async function renderNotifications(notifications) {
  const container = "#notificationsContainer";

  $(container).empty();

  if (notifications.length === 0) {
    $("#img-placeholder-ntf").removeClass("d-none");
  }

  // Iterate through each notification and clone the template
  notifications.forEach((notification) => {
    $("#img-placeholder-ntf").addClass("d-none");
    let template, newNtfCard;

    // Select the template based on the action type
    switch (notification.action) {
      case 1: // Subscribe
        template = "#subscribeNtfTemplate";
        break;
      case 2: // Unsubscribe
        template = "#unsubscribeNtfTemplate";
        break;
      default:
        console.warn(`Unknown action type: ${notification.action}`);
        return;
    }

    newNtfCard = $(template)
      .clone()
      .removeClass("template d-none d-sm-none")
      .addClass("d-sm-flex")
      .removeAttr("id");

    const uniqueId = `ntf_${notification.product_id}`;
    newNtfCard.attr("id", uniqueId);

    newNtfCard.find(".companyName").text(notification.supplicant_name);
    newNtfCard.find(".purposeLabel").text("Purpose of Usage");
    newNtfCard
      .find(".ntfDate")
      .text(extractDateNtfPart(notification.created_at));

    switch (notification.action) {
      case 1: // Subscribe
        newNtfCard
          .find(".notificationText")
          .text(
            `${notification.supplicant_name} has subscribed to your asset ${notification.product_label}.`
          );
        newNtfCard
          .find(".assetLink")
          .attr("id", `${uniqueId}_assetLink`)
          .attr("href", `#`)
          .off("click")
          .on("click", function () {
            info_handleGetDetails(notification.product_id);
            g_selection = {
              pid: notification.product_id,
              label: notification.product_label,
              date: "",
              side: "published",
            };
            $("#menuItemAsset").addClass("active");
            $("#menuItemNtf").removeClass("active");
          });
        break;
      case 2: // Unsubscribe
        newNtfCard
          .find(".notificationText")
          .text(
            `${notification.supplicant_name} has unsubscribed from your asset ${notification.product_label}.`
          );
        break;
    }

    newNtfCard
      .find(".purposeLink")
      .attr("id", `${uniqueId}_purposeLink`)
      .attr("href", notification.purpose_url);

    $(container).append(newNtfCard);
  });

  app_show("notificationsPage");
}

function extractDatePart(dateString) {
  const date = new Date(dateString);

  const options = { year: "numeric", month: "short", day: "numeric" };

  return date.toLocaleDateString(undefined, options);
}

function extractDateNtfPart(dateString) {
  const date = new Date(dateString);

  const dateOptions = { day: "2-digit", month: "long", year: "numeric" };
  const timeOptions = { hour: "2-digit", minute: "2-digit", hour12: false };

  const formattedDate = date.toLocaleDateString(undefined, dateOptions);
  const formattedTime = date.toLocaleTimeString(undefined, timeOptions);

  return `${formattedDate}, ${formattedTime}`;
}

function filterByStatus(array, type) {
  // Define the status value based on the type
  let statusValue;
  if (type === "granted") {
    statusValue = 1;
  } else if (type === "notGranted") {
    statusValue = 0;
  }

  // Filter the array based on the status value
  return array.filter((item) => item.status === statusValue);
}

function countSubscriptions(allSubscriptions) {
  const grantedCount = allSubscriptions.filter(
    (subscription) => subscription.status === 1
  ).length;
  const notGrantedCount = allSubscriptions.filter(
    (subscription) => subscription.status === 0
  ).length;
  return { grantedCount, notGrantedCount };
}

function downloadJSON(jsonData, filename) {
  var dataStr = JSON.stringify(jsonData);
  var blob = new Blob([dataStr], { type: "application/json" });
  var url = URL.createObjectURL(blob);

  var link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
}

/////
///// Event handlers for backend notification events
/////

function on_log(msgJSON) {
  console.log("Log event received: ", msgJSON);
}

function on_dop_products_list(msgJSON) {
  switch (msgJSON.task) {
    case TASK_PRODUCTS_OTHER:
      renderProductsAll(msgJSON.params.set);
      break;
    case TASK_PRODUCTS_PUBLISHED:
      publishedProds = msgJSON.params.set;
      renderProductsPublished(msgJSON.params.set);
      break;
    case TASK_PRODUCT_DETAILS_PUB:
      renderProductDetails(msgJSON.params.set[0], "pub");
      break;
    case TASK_PRODUCT_DETAILS_OTHER:
      renderProductDetails(msgJSON.params.set[0], "other");
      break;
    case TASK_PRODUCT_DETAILS_INFO:
      g_selection.date = extractDatePart(msgJSON.params.set[0].created_at);
      pub_handleViewSubscriptionsGranted(msgJSON.params.set[0].id);
      break;
    default:
      break;
  }
}

function on_dop_pub_configuration(msgJSON) {
  if (msgJSON.params.err === 0) {
    const configDataBase64 = msgJSON.params.config;
    const decodedString = atob(configDataBase64);
    const jsonConfig = JSON.parse(decodedString);
    downloadJSON(jsonConfig, `dop_pub_conf_${msgJSON.params.product_id}.json`);
  } else {
    alert("Pub download conf error " + msgJSON.params.err);
  }
}

function on_dop_account_info(msgJSON) {
  if (msgJSON.params.err === 0) {
    updateUsernameDisplay(msgJSON.params.info.username);
    updateScreenDisplay(msgJSON.params.info.screen);
    currentUser.accountID = msgJSON.params.info.account_id;
  } else {
    alert("Account info error " + msgJSON.params.err);
  }
}

function on_dop_product_subscriptions(msgJSON) {
  if (msgJSON.params.err === 0) {
    switch (msgJSON.task) {
      case TASK_GRANTED_SUBSCRIPTIONS:
        renderGrantRevokeSubscriptions(msgJSON.params.set, "granted");
        break;
      case TASK_NOT_GRANTED_SUBSCRIPTIONS:
        renderGrantRevokeSubscriptions(msgJSON.params.set, "notGranted");
        break;
      default:
        break;
    }
  } else {
    alert("Product subscriptions error " + msgJSON.params.err);
  }
}

function on_dop_subscription_grant(msgJSON) {
  if (msgJSON.params.err === 0) {
    if (msgJSON.params.phase === 1) {
      if ($("#followersGrantedContainer").is(":visible")) {
        pub_handleViewSubscriptionsGranted();
        app_show("followersGrantedContainer");
      } else if ($("#followersNotGrantedContainer").is(":visible")) {
        pub_handleViewSubscriptionsNotGranted();
        app_show("followersNotGrantedContainer");
      }
      if (msgJSON.params.original_session == currentUser.session) {
        alert("Approve successful");
      }
    }
  } else {
    if (msgJSON.params.original_session == currentUser.session) {
      alert("Approve error " + msgJSON.params.err);
    }
  }
}

function on_dop_subscription_revoke(msgJSON) {
  if (msgJSON.params.err === 0) {
    if (msgJSON.params.phase === 1) {
      if ($("#followersGrantedContainer").is(":visible")) {
        pub_handleViewSubscriptionsGranted();
        app_show("followersGrantedContainer");
      } else if ($("#followersNotGrantedContainer").is(":visible")) {
        pub_handleViewSubscriptionsNotGranted();
        app_show("followersNotGrantedContainer");
      }
      if (msgJSON.params.original_session == currentUser.session) {
        alert("Revoke successful");
      }
    }
  } else {
    if (msgJSON.params.original_session == currentUser.session) {
      alert("Revoke error " + msgJSON.params.err);
    }
  }
}

function on_rif_advertisement_list(msgJSON) {
  if (msgJSON.params.err === 0) {
    if (msgJSON.params.phase === 1) {
      renderBillboardAdvs(msgJSON.params.ads_list);
    }
  } else {
    alert("RIF advertisement list error " + msgJSON.params.err);
  }
}

function on_rif_advertisement_interest(msgJSON) {
  if (msgJSON.params.err === 0) {
    if (msgJSON.params.phase === 1) {
      alert("RIF advertisement interest succesfull");
    }
  } else {
    alert("RIF advertisement interest error " + msgJSON.params.err);
  }
}

function on_rif_actionable_products(msgJSON) {
  if (msgJSON.params.err === 0) {
    if (msgJSON.params.phase === 1) {
      if (msgJSON.task === TASK_ACTIONABLE_PRODUCTS_ACCEPT) {
        renderMultipleProductsModal(
          msgJSON.params.ads_id,
          msgJSON.params.products,
          "accept"
        );
      } else {
        renderMultipleProductsModal(
          msgJSON.params.ads_id,
          msgJSON.params.products,
          "reject"
        );
      }
    }
  } else {
    alert("RIF advertisement list error " + msgJSON.params.err);
  }
}

function on_rif_private_message_list(msgJSON) {
  if (msgJSON.params.err === 0) {
    if (msgJSON.params.phase === 1) {
      renderPrivateMsgs(msgJSON.params.private_messages);
    }
  } else {
    alert("RIF private message list error " + msgJSON.params.err);
  }
}

function on_rif_news_list(msgJSON) {
  if (msgJSON.params.err === 0) {
    if (msgJSON.params.phase === 1) {
      renderNotifications(msgJSON.params.notifications);
    }
  } else {
    alert("RIF notification list error " + msgJSON.params.err);
  }
}

function on_error(msgJSON) {
  alert("Error with event " + msgJSON.params.input_event);
  console.log("Error: ", msgJSON);
}

async function on_other(msgJSON) {
  switch (msgJSON.event) {
    case "dex_change_screen":
      if (msgJSON.params.err === 0) {
        alert("Change of screen name successful");
        updateScreenDisplay(msgJSON.params.new_screen_name);
      } else {
        alert("Change of screen name error: " + msgJSON.params.err);
      }
      break;
    case "dex_change_password":
      if (msgJSON.params.err === 0) {
        alert("Change of password successful");
      } else {
        alert("Change of password error: " + msgJSON.params.err);
      }
      break;
    default:
      break;
  }
}

// Set event listeners for notification events
function setEventListeners() {
  DOOF.addEventListener("log", on_log);
  DOOF.addEventListener("error", on_error);
  DOOF.addEventListener("other", on_other);
  DOOF.addEventListener("dop_products_list", on_dop_products_list);
  DOOF.addEventListener("dop_subscription_grant", on_dop_subscription_grant);
  DOOF.addEventListener("dop_subscription_revoke", on_dop_subscription_revoke);
  DOOF.addEventListener("dop_pub_configuration", on_dop_pub_configuration);
  DOOF.addEventListener("dop_account_info", on_dop_account_info);
  DOOF.addEventListener(
    "dop_product_subscriptions",
    on_dop_product_subscriptions
  );
  DOOF.addEventListener("rif_advertisement_list", on_rif_advertisement_list);
  DOOF.addEventListener("rif_actionable_products", on_rif_actionable_products);
  DOOF.addEventListener(
    "rif_advertisement_interest",
    on_rif_advertisement_interest
  );
  DOOF.addEventListener("rif_private_message_list", on_rif_private_message_list);
  DOOF.addEventListener("rif_news_list", on_rif_news_list);
}

// Main general event handler
async function handleEvents(message) {
  console.log("Received message: ", message.message);
}

/*
  Please note that if a page is present in a level, app_show function will
  hide all of the other pages on the same level
  For instance, app_show 'landingPage' will hide everything else
*/
let spa_layout = [
  ["landingPage", "welcomePage"],

  [
    "billboardPage",
    "productsPage",
    "productList",
    "allProducts",
    "allProductsList",
    "notificationsPage",
    "messagesPage",
    "usefulInfoPage",
    "settingsPage",
    "followersList",
    "productDetailsAll",
    "productDetailsPub",
    "usefulInfoPage",
  ],

  ["newAdv", "advAccepted", "advRejected"],

  ["followersList", "productDetail"],

  ["followersGrantedContainer", "followersNotGrantedContainer"],

  ["usefulInfoGlossary", "usefulInfoFAQ", "usefulInfoTutorial"],
];

function app_show(div_id) {
  spa_layout.forEach((level) => {
    if (level.includes(div_id)) {
      level.forEach((container) => {
        $("#" + container).hide();
      });
    }
  });

  g_active = div_id;
  $("#" + div_id).show();
}
