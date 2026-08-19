function showConfirm(message) {
  const overlay = document.querySelector("#confirm-overlay");
  const msgEl = document.querySelector("#confirm-message");
  const okBtn = document.querySelector("#confirm-ok");
  const cancelBtn = document.querySelector("#confirm-cancel");
  if (!overlay || !msgEl || !okBtn || !cancelBtn) return Promise.resolve(true);
  const i18n = window.I18N || {};
  msgEl.textContent = message;
  okBtn.textContent = i18n.confirm_ok || "확인";
  cancelBtn.textContent = i18n.confirm_cancel || "취소";
  overlay.hidden = false;
  return new Promise((resolve) => {
    const cleanup = (result) => {
      overlay.hidden = true;
      okBtn.removeEventListener("click", onOk);
      cancelBtn.removeEventListener("click", onCancel);
      resolve(result);
    };
    const onOk = () => cleanup(true);
    const onCancel = () => cleanup(false);
    okBtn.addEventListener("click", onOk);
    cancelBtn.addEventListener("click", onCancel);
  });
}
