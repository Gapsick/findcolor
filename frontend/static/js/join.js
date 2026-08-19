document.querySelector("#join-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.target.querySelector("button");
  button.disabled = true;
  const response = await fetch("/api/join", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nickname: document.querySelector("#nickname").value }),
  });
  const data = await response.json();
  if (response.ok) location.href = "/waiting";
  else {
    document.querySelector("#error").textContent = data.error;
    button.disabled = false;
  }
});
