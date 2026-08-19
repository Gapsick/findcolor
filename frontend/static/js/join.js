document.querySelectorAll(".avatar-option").forEach((option) => {
  option.addEventListener("click", () => {
    document.querySelector(".avatar-option.selected")?.classList.remove("selected");
    option.classList.add("selected");
  });
});

document.querySelector("#join-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.target.querySelector("button[type=submit]");
  button.disabled = true;
  const avatar = document.querySelector(".avatar-option.selected")?.dataset.avatar || "";
  const response = await fetch("/api/join", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nickname: document.querySelector("#nickname").value, avatar }),
  });
  const data = await response.json();
  if (response.ok) location.href = "/waiting";
  else {
    document.querySelector("#error").textContent = data.error;
    button.disabled = false;
  }
});
