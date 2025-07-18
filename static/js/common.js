"use strict";

const API_URL = "localhost:8000";
const ONLINE_CLASS = "online";
const CON_PREFIX = "d";

/** @type {Map<string, Conversation>} */
const conversations = new Map();
/** @type {Map<string, ChatEntry[]>} */
const chatEntries = new Map();
const conversationsCont = document.querySelector(`#conversations`);
const chatsPane = document.querySelector("#chatsPane");
const noChatsPlaceholder = document.querySelector("#nosel");
const pleaseWaitMsgPlaceholder = document.querySelector("#loadingCh");
const metrics = document.getElementById("metrics")
/** @type {Map<string, DoctorM>} */
const activeConnections = new Map();
const activeConnectionsCont = document.querySelector("#actCon");
/** @type {string|undefined} */
let curConvo = undefined;
/** @type {HTMLFormElement} */
const queryForm = document.getElementById("inpF");

queryForm.addEventListener("submit", function (e) {
  e.preventDefault();
  const fd = new FormData(queryForm);
  if (curConvo) {
    /** @type {string} */
    const msg = fd.get("query");
    if (msg.trim().length === 0) {
      return;
    }
    const convoId = curConvo.substring(1);
    const p = {
      msg,
      recvid: convoId,
    };
    ws.send(JSON.stringify(p));
    queryForm.reset();
    const ce = chatEntries.get(convoId);
    /** @type {ChatEntry} */
    const entry = {
      conversation_id: convoId,
      message: msg,
      from_doctor: IS_DOC,
      time: null,
      id: null,
    };
    ce && ce.push(entry);
    const div = createChatEntryDiv(entry);
    chatsPane.appendChild(div);
  } else {
    console.error("No connection payload found for current conversation");
  }
});

const ws = new WebSocket(`ws://${API_URL}/ws`);

ws.addEventListener("message", onMessageReceived);

/**
 *
 * @param {MessageEvent<string>} event
 */
function onMessageReceived(event) {
  const payload = Payload.fromString(event.data);
  if (payload === null) {
    console.error("Invalid payload received");
    return;
  }
  payload.process();
}

/**
 *
 * @param {MsgPayload} msg
 */
function showMessage(msg) {
  const ce = chatEntries.get(msg.sender_id);
  /** @type {ChatEntry} */
  const entry = {
    conversation_id: msg.sender_id,
    message: msg.msg,
    from_doctor: !IS_DOC,
    id: msg.sender_id,
    time: Date.now().toLocaleString(),
  };
  if (ce) {
    ce.push(entry);
  }
  if (curConvo && msg.sender_id === curConvo.substring(1)) {
    const div = createChatEntryDiv(entry);
    chatsPane.appendChild(div);
  }
}

class Payload {
  /** @type {PayloadType} */
  #type;
  #data;

  /**
   *
   * @param {PayloadType} type
   * @param {string} data
   */
  constructor(type, data) {
    this.#type = type;
    this.#data = data;
  }

  get type() {
    return this.#type;
  }

  process() {
    /** @type {Object} */
    let json;
    try {
      json = JSON.parse(this.#data);
    } catch (e) {
      console.error(`Invalid payload data: {e}`);
      return;
    }
    switch (this.#type) {
      case PayloadType.CONN:
        if (!Object.hasOwn(json, "id") && !Object.hasOwn(json, "wsip")) {
          console.error("Invalid connect payload");
          return;
        }
        const conn = new ConPayload(json["id"]);
        onConnect(conn);
        break;
      case PayloadType.DISCON:
        if (!Object.hasOwn(json, "id")) {
          console.error("Invalid disconnect payload");
          return;
        }
        const discon = new DisconPayload(json["id"]);
        onDisconnect(discon);
        break;
      case PayloadType.MSG:
        if (!Object.hasOwn(json, "msg") && !Object.hasOwn(json, "sender_id")) {
          console.error("Invalid message payload");
          return;
        }
        const msg = new MsgPayload(json["msg"], json["sender_id"]);
        showMessage(msg);
        break;
      default:
        console.warn("Type for message not found: ", this.#type);
    }
  }

  /**
   *
   * @param {string} json
   * @returns {Payload | null}
   */
  static fromString(json) {
    try {
      const j = JSON.parse(json);
      if (!Object.hasOwn(j, "type") && !Object.hasOwn(j, "data")) {
        console.error(`Invalid message payload received: ${j}`);
        return null;
      }
      const ty = getPayloadType(j.type);
      if (!ty) {
        console.error("Couldn't get payload type aborting");
        return null;
      }
      return new Payload(ty, j.data);
    } catch (e) {
      console.error(e);
      return null;
    }
  }
}

/**
 *
 * @param {DisconPayload} disconn
 */
function onDisconnect(disconn) {
  if (conversations.has(disconn.id)) {
    console.log("Changing online status");
    const c = conversations.get(disconn.id);
    if (c === undefined) {
      return;
    }
    c.onlineStatus = false;
    conversations.set(c.id, c);
    const conv = document.querySelector(`#${CON_PREFIX}${disconn.id}`);
    if (conv) {
      conv.classList.remove(ONLINE_CLASS);
    }
  } else {
    console.log("Removing an active connection");
    const elem = document.querySelector(`#${CON_PREFIX}${disconn.id}`);
    if (elem) {
      elem.remove();
    }
    activeConnections.delete(disconn.id);
  }
}

function onConversationClicked(event) {
  /** @type {HTMLDivElement} */
  let target = event.target;
  if (target.id === "") {
    target = target.parentElement;
  }

  const cid = target.id.substring(1);

  if (target.id === curConvo) {
    return;
  }
  const curConvoELe = document.getElementById(curConvo);
  curConvoELe && curConvoELe.classList.remove("bg-gray-100");

  while (chatsPane.hasChildNodes()) {
    chatsPane.removeChild(chatsPane.firstChild);
  }

  if (noChatsPlaceholder) {
    noChatsPlaceholder.classList.add("hidden");
  }
  if (pleaseWaitMsgPlaceholder) {
    pleaseWaitMsgPlaceholder.classList.remove("hidden");
  }

  // show entries form cache
  const entries = chatEntries.get(cid);
  if (entries === undefined) {
    console.error("No chat entries for conversation with id: ", cid);
    console.error("Aborting");
    if (pleaseWaitMsgPlaceholder) {
      pleaseWaitMsgPlaceholder.classList.add("hidden");
    }
    if (noChatsPlaceholder) {
      noChatsPlaceholder.classList.remove("hidden");
    }
    return;
  }
  entries
    .map((e) => {
      return createChatEntryDiv(e);
    })
    .forEach((e) => {
      chatsPane.appendChild(e);
    });
  if (pleaseWaitMsgPlaceholder) {
    pleaseWaitMsgPlaceholder.classList.add("hidden");
  }
  curConvo = target.id;
  target.classList.add("bg-gray-100");
  if (metrics) {
    metrics.classList.remove("hidden")
  }
}

class Conversation {
  /**
   *
   * @param {string} name
   * @param {string} id
   * @param {boolean} onlineStatus
   */
  constructor(name, id, onlineStatus) {
    this.name = name;
    this.id = id;
    this.onlineStatus = onlineStatus;
  }
}

class DisconPayload {
  /**
   *
   * @param {string} id
   */
  constructor(id) {
    this.id = id;
  }
}

class ConPayload {
  /**
   *
   * @param {string} id;
   */
  constructor(id) {
    this.id = id;
  }
}

class MsgPayload {
  /**
   *
   * @param {string} msg
   * @param {string} sender_id
   */
  constructor(msg, sender_id) {
    this.msg = msg;
    this.sender_id = sender_id;
  }
}

/**
 * Enum for common PayloadType.
 * @readonly
 * @enum {string}
 */
const PayloadType = Object.freeze({
  DISCON: "disconnect",
  CONN: "connect",
  MSG: "message",
});

/**
 *
 * @param {ChatEntry} e
 * @returns {HTMLDivElement}
 */
function createChatEntryDiv(e) {
  const div = document.createElement("div");
  if (e.from_doctor === !IS_DOC) {
    div.className = "flex items-start gap-1 mb-4";
    div.innerHTML = `
          <div
            class="bg-white text-gray-800 px-4 py-2 rounded-lg shadow-sm max-w-md"
          >
            ${e.message}
          </div>
        `;
  } else {
    div.className = "flex items-start space-x-3 mb-4 flex-row-reverse gap-1";
    div.innerHTML = `
          <div
            class="bg-blue-500 text-white px-4 py-2 rounded-lg shadow-sm max-w-md"
          >
            ${e.message}
          </div>
      `;
  }
  return div;
}

/**
 *
 * @param {string} type
 * @returns {PayloadType | null}
 */
function getPayloadType(type) {
  switch (type) {
    case PayloadType.DISCON:
      return PayloadType.DISCON;
    case PayloadType.CONN:
      return PayloadType.CONN;
    case PayloadType.MSG:
      return PayloadType.MSG;
    default:
      return null;
  }
}

/**
 * @typedef {Object} ChatEntry
 * @property {number} id
 * @property {string} time
 * @property {boolean} from_doctor
 * @property {string} message
 * @property {string} conversation_id
 */
/**
 * @typedef {Object} EntriesRes
 * @property {ChatEntry[]} entries
 */

/**
 * @typedef {Object} Conversations
 * @property {Conversation[]} conversations
 */

/**
 * @typedef {Object} DoctorM
 * @property {string} email
 * @property {string} name
 * @property {string} id
 * @property {string[]} qualifications
 */
