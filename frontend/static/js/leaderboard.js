const tr = (key, values = {}) => Object.entries(values).reduce(
  (text, [name, value]) => text.replaceAll(`{${name}}`, value), window.I18N[key] || key
);

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = value;
  return element.innerHTML;
}

function medal(rank) {
  return { 1: "🥇", 2: "🥈", 3: "🥉" }[rank] || `${rank}${tr("rank_suffix")}`;
}

function renderLeaderboard(list) {
  document.querySelector("#leaderboard").innerHTML = list.map((entry, index) => {
    const rank = index + 1;
    const rankClass = rank <= 3 ? ` rank-${rank}` : "";
    const meClass = entry.me ? " me" : "";
    return `<li class="rank-row${rankClass}${meClass}"><span class="rank-medal">${medal(rank)}</span><span class="rank-name"><span class="mini-avatar">${entry.avatar}</span>${escapeHtml(entry.nickname)}${entry.me ? ` (${tr("me")})` : ""}</span><span class="rank-score">${entry.total_score}${tr("points")}</span></li>`;
  }).join("");
}

let busy = false;
let navigating = false;
let revealedShown = false;

async function refresh() {
  if (busy || navigating) return;
  busy = true;
  try {
    const response = await fetch("/api/state");
    if (response.status === 401) { location.href = "/join"; return; }
    const data = await response.json();
    if (data.status === "waiting") { location.href = "/join"; return; }
    if (data.status === "playing") {
      navigating = true;
      await runCountdown();
      location.href = "/play";
      return;
    }
    if (data.is_final_round) {
      if (data.results_revealed) {
        document.querySelector("#final-suspense-section").hidden = true;
        document.querySelector("#podium-section").hidden = false;
        if (!revealedShown) {
          revealedShown = true;
          burstConfetti();
        }
        renderPodium(data.leaderboard, "#podium-section");
      }
      return;
    }
    renderLeaderboard(data.leaderboard);
  } finally {
    busy = false;
  }
}

refresh();
setInterval(refresh, 1000);
