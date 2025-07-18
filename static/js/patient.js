"use strict";

const IS_DOC = false;
(async function () {
  const r = await fetch(`http://${API_URL}/patient/conversation`);
  if (!r.ok) {
    console.error("Failed to fetch conversations");
    const t = await r.text();
    console.error(t);
    return;
  }

  /** @type {Conversations} */
  const j = await r.json();
  j.conversations.forEach((c) => {
    conversations.set(c.id, c);

    const li = document.createElement("li");
    li.id = CON_PREFIX + c.id;
    li.className = "p-4 border-b border-gray-200 cursor-pointer hover:bg-blue-50 transition duration-150 ease-in-out";
    li.innerHTML = `<span class="text-gray-700 font-medium">${c.name}</span>`;

    li.addEventListener("click", onConversationClicked);

    if (conversationsCont) {
      conversationsCont.prepend(li);
    }
  });

  const entriesReqs = j.conversations.map((c) =>
    fetch(`http://${API_URL}/patient/conversation/entries?docId=${c.id}`)
      .then((r) => {
        if (!r.ok) {
          console.error("error fetching chat entries for chat ", c.id);
          r.text().then((t) => console.error(t));
          return null;
        }
        return r.json();
      })
      .then((e) => {
        if (e !== null) {
          /** @type {EntriesRes} */
          const json = e;
          return [c.id, json];
        }
        return [c.id, { entries: [] }];
      })
  );

  const entriesResp = await Promise.all(entriesReqs);
  
  entriesResp.forEach((e) => {
    chatEntries.set(e[0], e[1].entries);
  });
})();

/**
 *
 * @param {ConPayload} conn
 */
function onConnect(conn) {
  if (conversations.has(conn.id)) {
   conversations.get(conn.id).onlineStatus = true;
    // update ui
    const conv = document.querySelector(`#${CON_PREFIX}${conn.id}`);
    if (conv) {
      conv.classList.add(ONLINE_CLASS);
    }
  } else {
    console.log("Fetching doctor");
    if (activeConnectionsCont) {
      fetch(`http://${API_URL}/get/doctor/${conn.id}`)
        .then((r) => {
          if (!r.ok) {
            r.text().then((t) => console.error(`Error getting doc info: ${t}`));
            return;
          }
          return r.json();
        })
        .then((json) => {
          if (json) {
            /** @type {DoctorM} */
            const data = JSON.parse(json);
            activeConnections.set(data.id, data);

            const div = document.createElement("div");
            div.className = "flex items-center space-x-4 w-max cursor-pointer";
            div.id = CON_PREFIX + data["id"];
            div.innerHTML = `
            <div class="relative">
              <div class="rounded-full w-12 h-12 bg-blue-500 text-white grid place-content-center text-xl font-semibold">
                <p>${data.name[0].toUpperCase()}</p>
              </div>
              <div class="absolute w-3 h-3 bg-green-400 rounded-full right-0 top-0 animate-ping"></div>
              </div>
               <p class="text-sm font-medium text-gray-800 truncate">Dr. ${data.name}</p>
          `;
            div.addEventListener("click", onActiveConnectionClicked);
            console.log("Updating ui with new available doctor");
            activeConnectionsCont.appendChild(div);
          }
        });
    }
  }
}

function onActiveConnectionClicked(event) {
  /** @type {HTMLDivElement} */
  let target = event.target;
  while (target.id.trim().length === 0) {
    target = target.parentElement;
    if (target === null) {
      break;
    }
  }
  const c = activeConnections.get(target.id.substring(1));
  if (c === undefined) {
    return;
  }

  if (conversations.has(c.id)) {
    return;
  }

  conversations.set(c.id, new Conversation(c.name, c.id, true));

  const fd = new FormData();
  fd.set("id", c.id);
  fetch(`http://${API_URL}/patient/conversation`, {
    method: "POST",
    body: fd,
  }).then((r) => {
    if (!r.ok) {
      return;
    }
    
    const li = document.createElement("li");
    li.id = CON_PREFIX + c.id;
    li.className = "p-4 border-b border-gray-200 cursor-pointer hover:bg-blue-50 transition duration-150 ease-in-out";
    li.innerHTML = `<span class="text-gray-700 font-medium">${c.name}</span>`;

    li.addEventListener("click", onActiveConnectionClicked);

    if (conversationsCont) {
      conversationsCont.prepend(li);
      target.remove();
    }
  });
}

/**
 * @typedef {Object} DoctorM
 * @property {string} email
 * @property {string} name
 * @property {string} id
 * @property {string[]} qualifications
 */