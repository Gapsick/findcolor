function resultsTr(key, values = {}) {
  const source = (window.I18N && window.I18N[key]) || key;
  return Object.entries(values).reduce(
    (text, [name, value]) => text.replaceAll(`{${name}}`, value), source
  );
}

function resultsEscapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = value;
  return element.innerHTML;
}

function renderPodium(list, containerSelector) {
  const container = document.querySelector(containerSelector);
  if (!container) return;
  const top3 = list.slice(0, 3);
  const rest = list.slice(3);
  const medals = ["🥇", "🥈", "🥉"];
  const podiumHtml = `<div class="podium">${top3.map((entry, i) => `
    <div class="podium-slot podium-${i + 1}${entry.me ? " me" : ""}">
      <div class="podium-medal">${medals[i]}</div>
      <div class="podium-bar">
        <div class="podium-name"><span class="mini-avatar">${entry.avatar}</span>${resultsEscapeHtml(entry.nickname)}${entry.me ? ` (${resultsTr("me")})` : ""}</div>
        <div class="podium-score">${entry.total_score}${resultsTr("points")}</div>
      </div>
    </div>`).join("")}</div>`;
  const restHtml = rest.length ? `<ol class="leaderboard rest-list">${rest.map((entry, idx) => `
    <li class="rank-row${entry.me ? " me" : ""}"><span class="rank-medal">${idx + 4}${resultsTr("rank_suffix")}</span><span class="rank-name"><span class="mini-avatar">${entry.avatar}</span>${resultsEscapeHtml(entry.nickname)}${entry.me ? ` (${resultsTr("me")})` : ""}</span><span class="rank-score">${entry.total_score}${resultsTr("points")}</span></li>`).join("")}</ol>` : "";
  container.innerHTML = podiumHtml + restHtml;
}

function burstConfetti() {
  const layer = document.createElement("div");
  layer.className = "confetti-layer";
  document.body.appendChild(layer);
  const colors = ["#ffc93c", "#2fe6d9", "#ff4d6d", "#4ee08a", "#ff8fab"];
  const pieces = 70;
  for (let i = 0; i < pieces; i += 1) {
    const piece = document.createElement("div");
    piece.className = "confetti-piece";
    piece.style.left = `${Math.random() * 100}%`;
    piece.style.background = colors[i % colors.length];
    piece.style.animationDelay = `${Math.random() * 0.4}s`;
    piece.style.animationDuration = `${2.2 + Math.random() * 1.2}s`;
    piece.style.setProperty("--drift", `${(Math.random() - 0.5) * 160}px`);
    layer.appendChild(piece);
  }
  setTimeout(() => { layer.remove(); }, 3800);
}
