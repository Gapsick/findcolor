function runCountdown() {
  const overlay = document.querySelector("#countdown-overlay");
  const numberEl = document.querySelector("#countdown-number");
  if (!overlay || !numberEl) return Promise.resolve();
  const steps = ["3", "2", "1", (window.I18N && window.I18N.go) || "GO!"];
  return new Promise((resolve) => {
    overlay.hidden = false;
    let i = 0;
    const tick = () => {
      numberEl.textContent = steps[i];
      numberEl.classList.remove("pop");
      // eslint-disable-next-line no-unused-expressions
      numberEl.offsetWidth; // 애니메이션 재시작을 위한 리플로우 강제
      numberEl.classList.add("pop");
      i += 1;
      if (i < steps.length) {
        setTimeout(tick, 700);
      } else {
        setTimeout(() => { overlay.hidden = true; resolve(); }, 650);
      }
    };
    tick();
  });
}
