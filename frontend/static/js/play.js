const tr = (key, values = {}) => Object.entries(values).reduce(
  (text, [name, value]) => text.replaceAll(`{${name}}`, value), window.I18N[key] || key
);

const photoInput = document.querySelector("#photo");
const submitButton = document.querySelector("#submit-photo");
const form = document.querySelector("#photo-form");

photoInput.addEventListener("change", () => {
  const file = photoInput.files[0];
  if (!file) return;
  const preview = document.querySelector("#local-preview");
  preview.src = URL.createObjectURL(file);
  preview.style.display = "block";
  submitButton.disabled = false;
});

let redirecting = false;

async function refreshTimer() {
  if (redirecting) return;
  const response = await fetch("/api/state");
  if (!response.ok) return;
  const data = await response.json();
  document.querySelector("#timer").textContent = data.remaining;
  if (data.status === "round_result") {
    if (document.querySelector("#result").hidden) {
      submitButton.disabled = true;
      document.querySelector("#error").textContent = tr("time_closed");
    }
    redirecting = true;
    clearInterval(pollTimer);
    setTimeout(() => { location.href = "/leaderboard"; }, 1500);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  form.hidden = true;
  document.querySelector("#analysis-wait").hidden = false;
  const response = await fetch("/api/submit", { method: "POST", body: new FormData(form) });
  const data = await response.json();
  if (!response.ok) {
    form.hidden = false;
    document.querySelector("#analysis-wait").hidden = true;
    document.querySelector("#error").textContent = data.error;
    submitButton.textContent = tr("analyze_photo");
    submitButton.disabled = false;
    return;
  }
  document.querySelector("#analysis-wait").hidden = true;
  document.querySelector("#result").hidden = false;
  document.querySelector("#result-photo").src = data.preview;
  document.querySelector("#found-color").style.background = data.representative || "transparent";
  document.querySelector("#found-code").textContent = data.representative || tr("none");
  document.querySelector("#color-score").textContent = `${data.color_score}${tr("points")}`;
  document.querySelector("#time-score").textContent = `${data.time_score}${tr("points")}`;
  document.querySelector("#final-score").textContent = `${data.final_score}${tr("points")}`;
  const similarity = Math.max(0, Math.min(100, data.color_score));
  document.querySelector("#similarity-value").textContent = `${data.color_score}${tr("points")}`;
  document.querySelector("#similarity-fill").style.width = `${similarity}%`;
  if (!data.match_found) {
    document.querySelector("#match-message").textContent = tr("no_match");
  } else if (data.selection_type === "object") {
    document.querySelector("#match-message").textContent = tr("object_match", { ratio: data.match_ratio });
  } else {
    document.querySelector("#match-message").textContent = tr("region_match", { ratio: data.match_ratio });
  }
});

refreshTimer();
const pollTimer = setInterval(refreshTimer, 500);
