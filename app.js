const closeNavigation = (navigation, toggle, backdrop) => {
  navigation?.classList.remove("is-open");
  toggle?.setAttribute("aria-expanded", "false");
  backdrop?.classList.remove("is-open");
  document.body.classList.remove("navigation-open");
};

document.querySelectorAll(".nav-toggle[aria-controls]").forEach((toggle) => {
  const navigation = document.getElementById(toggle.getAttribute("aria-controls"));
  const isPortalMenu = toggle.classList.contains("portal-nav-toggle");
  const backdrop = isPortalMenu ? document.querySelector(".sidebar-backdrop") : null;

  if (!navigation) return;

  toggle.addEventListener("click", () => {
    const isOpen = navigation.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(isOpen));
    backdrop?.classList.toggle("is-open", isOpen);
    document.body.classList.toggle("navigation-open", isPortalMenu && isOpen);
    if (isOpen) navigation.querySelector("a")?.focus();
  });

  navigation.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => closeNavigation(navigation, toggle, backdrop));
  });

  backdrop?.addEventListener("click", () => closeNavigation(navigation, toggle, backdrop));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && navigation.classList.contains("is-open")) {
      closeNavigation(navigation, toggle, backdrop);
      toggle.focus();
    }
  });
});

document.querySelectorAll(".flash-close").forEach((button) => {
  button.addEventListener("click", () => button.closest(".flash")?.remove());
});

document.querySelectorAll("[data-table-search]").forEach((input) => {
  const table = document.getElementById(input.dataset.tableSearch);
  const noResults = table?.closest(".content-card")?.querySelector(".table-no-results");
  const emptyRow = table?.querySelector(".empty-table-row");
  const rows = table ? [...table.querySelectorAll("tbody tr:not(.empty-table-row)")] : [];

  if (!table) return;

  input.addEventListener("input", () => {
    const query = input.value.trim().toLocaleLowerCase();
    let visibleRows = 0;
    rows.forEach((row) => {
      const matches = row.textContent.toLocaleLowerCase().includes(query);
      row.hidden = !matches;
      if (matches) visibleRows += 1;
    });
    if (noResults) noResults.hidden = visibleRows > 0 || rows.length === 0 || Boolean(emptyRow);
  });
});

document.querySelectorAll("table").forEach((table) => {
  const body = table.tBodies[0];
  if (!body) return;

  table.querySelectorAll("[data-sort-column]").forEach((button) => {
    button.addEventListener("click", () => {
      const column = Number(button.dataset.sortColumn);
      const header = button.closest("th");
      const ascending = header?.getAttribute("aria-sort") !== "ascending";
      const rows = [...body.rows].filter((row) => !row.classList.contains("empty-table-row"));

      rows.sort((first, second) => {
        const left = first.cells[column]?.textContent.trim() ?? "";
        const right = second.cells[column]?.textContent.trim() ?? "";
        const leftNumber = Number(left);
        const rightNumber = Number(right);
        const comparison = left !== "" && right !== "" && !Number.isNaN(leftNumber) && !Number.isNaN(rightNumber)
          ? leftNumber - rightNumber
          : left.localeCompare(right, undefined, { numeric: true, sensitivity: "base" });
        return ascending ? comparison : -comparison;
      });

      rows.forEach((row) => body.append(row));
      table.querySelectorAll("th[aria-sort]").forEach((cell) => cell.setAttribute("aria-sort", "none"));
      header?.setAttribute("aria-sort", ascending ? "ascending" : "descending");
    });
  });
});

document.querySelectorAll("form[method='post']").forEach((form) => {
  form.addEventListener("submit", () => {
    const submitButton = form.querySelector("button[type='submit'], input[type='submit']");
    if (!submitButton || submitButton.disabled) return;
    submitButton.disabled = true;
    submitButton.setAttribute("aria-busy", "true");
    if (submitButton instanceof HTMLButtonElement) {
      submitButton.dataset.originalLabel = submitButton.textContent.trim();
      submitButton.textContent = form.action.endsWith("/logout") ? "Signing out…" : "Saving…";
    }
  });
});
