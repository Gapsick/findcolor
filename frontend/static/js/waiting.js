const tr = (key, values = {}) => Object.entries(values).reduce(
  (text, [name, value]) => text.replaceAll(`{${name}}`, value), window.I18N[key] || key
);

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = value;
  return element.innerHTML;
}

let busy = false;
let navigating = false;

async function refresh() {
  if (busy || navigating) return;
  busy = true;
  try {
    const response = await fetch("/api/state");
    if (response.status === 401) { location.href = "/join"; return; }
    const data = await response.json();
    if (data.status === "playing") {
      navigating = true;
      await runCountdown();
      location.href = "/play";
      return;
    }
    document.querySelector("#count").textContent = tr("current_players", { count: data.players.length });
    document.querySelector("#players").innerHTML = data.players.map((player) =>
      `<li class="player"><strong><span class="mini-avatar">${player.avatar}</span>${escapeHtml(player.nickname)}${player.me ? ` (${tr("me")})` : ""}</strong><span class="badge ready">${tr("joined")}</span></li>`
    ).join("");
  } finally {
    busy = false;
  }
}

refresh();
setInterval(refresh, 1000);
