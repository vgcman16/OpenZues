const autosize = (element) => {
  element.style.height = "auto";
  element.style.height = `${Math.max(element.scrollHeight, 120)}px`;
};

const restoreDrafts = () => {
  document.querySelectorAll("[data-draft-key]").forEach((scope) => {
    const key = scope.getAttribute("data-draft-key");
    if (!key) {
      return;
    }
    const status = scope.querySelector("[data-draft-status]");
    let restored = false;
    const payload = window.localStorage.getItem(`forumforge:${key}`);
    const parsed = payload ? JSON.parse(payload) : {};

    scope.querySelectorAll("[data-draft-field]").forEach((field) => {
      const name = field.getAttribute("data-draft-field");
      if (!name) {
        return;
      }
      if (parsed[name]) {
        field.value = parsed[name];
        restored = true;
      }
      if (field.tagName === "TEXTAREA") {
        autosize(field);
      }
      field.addEventListener("input", () => {
        const next = {};
        scope.querySelectorAll("[data-draft-field]").forEach((draftField) => {
          const draftName = draftField.getAttribute("data-draft-field");
          if (draftName) {
            next[draftName] = draftField.value;
          }
        });
        window.localStorage.setItem(`forumforge:${key}`, JSON.stringify(next));
        if (field.tagName === "TEXTAREA") {
          autosize(field);
        }
      });
    });

    scope.addEventListener("submit", () => {
      window.localStorage.removeItem(`forumforge:${key}`);
    });

    if (status && restored) {
      status.hidden = false;
    }
  });
};

document.addEventListener("DOMContentLoaded", () => {
  restoreDrafts();
});
