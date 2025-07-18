"use strict";


const IS_DOC = true;
(async function () {
  const r = await fetch(`http://${API_URL}/doctor/conversation`);
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
    fetch(`http://${API_URL}/doctor/conversation/entries?patId=${c.id}`)
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
  }
}



