const slider = document.querySelector("#step-slider");
const dots = document.querySelectorAll("#slider-dots .dot");
const prevButton = document.querySelector("#slider-prev");
const nextButton = document.querySelector("#slider-next");
const stepCount = dots.length;

function currentIndex() {
  return Math.round(slider.scrollLeft / slider.clientWidth);
}

function setActiveDot(index) {
  dots.forEach((dot, i) => dot.classList.toggle("active", i === index));
  prevButton.disabled = index <= 0;
  nextButton.disabled = index >= stepCount - 1;
}

function goToStep(index) {
  const clamped = Math.max(0, Math.min(stepCount - 1, index));
  slider.scrollTo({ left: clamped * slider.clientWidth, behavior: "smooth" });
}

dots.forEach((dot) => {
  dot.addEventListener("click", () => goToStep(Number(dot.dataset.index)));
});
prevButton.addEventListener("click", () => goToStep(currentIndex() - 1));
nextButton.addEventListener("click", () => goToStep(currentIndex() + 1));

let ticking = false;
slider.addEventListener("scroll", () => {
  if (ticking) return;
  ticking = true;
  requestAnimationFrame(() => {
    setActiveDot(currentIndex());
    ticking = false;
  });
});

setActiveDot(0);
