const tr = (key, values = {}) => Object.entries(values).reduce(
  (text, [name, value]) => text.replaceAll(`{${name}}`, value), window.I18N[key] || key
);

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = value;
  return element.innerHTML;
}

function submissionLabel(player) {
  if (player.submission_status === "processing") {
    return `<span class="badge processing">${tr("processing")}</span>`;
  }
  if (player.submission_status === "completed") {
    const score = player.score?.final_score;
    return `<span class="badge completed">${tr("complete")}${score == null ? "" : ` · ${score}${tr("points")}`}</span>`;
  }
  return `<span class="badge">${tr("not_submitted")}</span>`;
}

function renderSubmissionProgress(data, countSelector, listSelector) {
  document.querySelector(countSelector).textContent =
    tr("progress", { done: data.submitted_count, processing: data.processing_count, total: data.players.length });
  document.querySelector(listSelector).innerHTML = data.players.map((player) =>
    `<li class="player"><strong>${escapeHtml(player.nickname)}</strong>${submissionLabel(player)}</li>`
  ).join("");
}

function medal(rank) {
  return { 1: "🥇", 2: "🥈", 3: "🥉" }[rank] || `${rank}${tr("rank_suffix")}`;
}

function renderLeaderboard(list) {
  document.querySelector("#leaderboard").innerHTML = list.map((entry, index) => {
    const rank = index + 1;
    const rankClass = rank <= 3 ? ` rank-${rank}` : "";
    return `<li class="rank-row${rankClass}"><span class="rank-medal">${medal(rank)}</span><span class="rank-name">${escapeHtml(entry.nickname)}</span><span class="rank-score">${entry.total_score}${tr("points")}</span></li>`;
  }).join("");
}

function roundBadge(data) {
  return `${tr("round_label")} ${data.round}/${data.total_rounds}`;
}

let busy = false;
let lastStatus = null;
let revealedShown = false;

async function refresh() {
  if (busy) return;
  busy = true;
  try {
    const response = await fetch("/api/state?admin=1");
    if (response.status === 403) { location.href = "/admin"; return; }
    const data = await response.json();
    const playing = data.status === "playing";
    const roundResult = data.status === "round_result";

    if (playing && lastStatus !== "playing") {
      lastStatus = "playing";
      await runCountdown();
    } else {
      lastStatus = data.status;
    }

    document.querySelector("#waiting-view").hidden = playing || roundResult;
    document.querySelector("#playing-view").hidden = !playing;
    document.querySelector("#result-view").hidden = !roundResult;

    if (roundResult) {
      document.querySelector("#result-round-badge").textContent = roundBadge(data);
      document.querySelector("#result-title").textContent =
        data.is_final_round ? tr("final_results_title") : tr("round_result_title");

      document.querySelector("#round-leaderboard-section").hidden = data.is_final_round;
      document.querySelector("#final-suspense-section").hidden = !(data.is_final_round && !data.results_revealed);
      document.querySelector("#podium-section").hidden = !(data.is_final_round && data.results_revealed);

      if (!data.is_final_round) {
        renderLeaderboard(data.leaderboard);
      } else if (data.results_revealed) {
        if (!revealedShown) {
          revealedShown = true;
          burstConfetti();
        }
        renderPodium(data.leaderboard, "#podium-section");
      }
      return;
    }
    revealedShown = false;
    if (playing) {
      document.querySelector("#playing-round-badge").textContent = roundBadge(data);
      document.querySelector("#target").style.background = data.target;
      document.querySelector("#target-code").textContent = `${data.target_name} · ${data.target}`;
      document.querySelector("#timer").textContent = data.remaining;
      renderSubmissionProgress(data, "#progress-count", "#progress-players");
      return;
    }
    document.querySelector("#count").textContent = tr("players", { count: data.players.length });
    document.querySelector("#players").innerHTML = data.players.map((player) =>
      `<li class="player"><strong>${escapeHtml(player.nickname)}</strong><span class="badge ready">${tr("joined")}</span></li>`
    ).join("");
    const canStart = data.players.length > 0;
    const button = document.querySelector("#start");
    button.disabled = !canStart;
    button.textContent = canStart ? "START" : tr("start_after_join");
  } finally {
    busy = false;
  }
}

document.querySelector("#start").addEventListener("click", async () => {
  if (await showConfirm(tr("confirm_start"))) await fetch("/api/start", { method: "POST" });
  refresh();
});
document.querySelector("#next-round").addEventListener("click", async () => {
  if (await showConfirm(tr("confirm_next_round"))) await fetch("/api/next_round", { method: "POST" });
  refresh();
});
document.querySelector("#reveal-button").addEventListener("click", async () => {
  await fetch("/api/reveal_results", { method: "POST" });
  refresh();
});
document.querySelector("#reset").addEventListener("click", async () => {
  if (await showConfirm(tr("confirm_reset"))) await fetch("/api/reset", { method: "POST" });
  lastStatus = null;
  revealedShown = false;
  refresh();
});

refresh();
setInterval(refresh, 1000);
