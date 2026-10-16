const clock = document.getElementById("local-clock");
if (clock) {
  const updateClock = () => {
    clock.textContent = new Date().toLocaleString(undefined, {
      weekday: "short",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };
  updateClock();
  window.setInterval(updateClock, 30000);
}

document.querySelectorAll(".flash-close").forEach((button) => {
  button.addEventListener("click", () => button.closest(".flash")?.remove());
});

const formatRemaining = (seconds) => {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return minutes > 0 ? `${minutes}m ${remainder}s remaining` : `${remainder}s remaining`;
};

document.querySelectorAll("[data-expiry]").forEach((element) => {
  const expiry = new Date(`${element.dataset.expiry}Z`).getTime();
  const update = () => {
    const left = Math.max(0, Math.ceil((expiry - Date.now()) / 1000));
    element.textContent = left ? formatRemaining(left) : "Expiring; refresh to update";
  };
  update();
  window.setInterval(update, 1000);
});

const detailCountdown = document.getElementById("detail-countdown");
if (detailCountdown) {
  let remaining = Number(detailCountdown.dataset.remainingSeconds || 0);
  const update = () => {
    const minutes = Math.floor(remaining / 60);
    const seconds = remaining % 60;
    detailCountdown.textContent = remaining > 0 ? `${minutes}m ${seconds}s` : "Expired";
    remaining = Math.max(0, remaining - 1);
  };
  update();
  window.setInterval(update, 1000);
}