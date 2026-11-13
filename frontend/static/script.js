const tagSearch = document.querySelector("#tag-search");
const tagSelect = document.querySelector("#tag");
const tagHelp = document.querySelector("#tag-help");
const snapshotStatus = document.querySelector("#snapshot-status");
const snapshotTime = document.querySelector("#snapshot-time");

function showSnapshotTime(timestamp) {
    if (!timestamp || !snapshotTime || !snapshotStatus) {
        return;
    }
    const downloaded = new Date(timestamp);
    snapshotTime.dateTime = timestamp;
    snapshotTime.textContent = downloaded.toLocaleTimeString([], {
        hour: "numeric",
        minute: "2-digit",
        timeZoneName: "short",
    });
    snapshotTime.title = downloaded.toLocaleString();
    snapshotStatus.hidden = false;
}

showSnapshotTime(snapshotTime?.dateTime);

const filterToggle = document.querySelector("#filter-toggle");
const filterPanel = document.querySelector("#filter-panel");

function setFiltersOpen(open) {
    filterPanel.hidden = !open;
    filterToggle.setAttribute("aria-expanded", String(open));
    filterToggle.textContent = open ? "Hide Filters" : "Show Filters";
}

if (filterToggle && filterPanel) {
    setFiltersOpen(filterPanel.dataset.startOpen === "true");
    filterToggle.hidden = false;
    filterToggle.addEventListener("click", () => setFiltersOpen(filterPanel.hidden));
    filterToggle.form.addEventListener("invalid", () => setFiltersOpen(true), true);
}

if (tagSearch && tagSelect && tagHelp) {
    const [allTags, ...initialOptions] = tagSelect.options;
    let tagOptions = initialOptions;
    const suggestionLimit = 10;

    function updateTagOptions() {
        const query = tagSearch.value.trim().toLowerCase();
        const selectedOption = tagSelect.selectedOptions[0] || allTags;
        const matches = tagOptions.filter((option) => option.value.includes(query));
        const visibleOptions = matches.slice(0, suggestionLimit);

        if (selectedOption !== allTags && !visibleOptions.includes(selectedOption)) {
            visibleOptions.unshift(selectedOption);
        }

        tagSelect.replaceChildren(allTags, ...visibleOptions);
        tagSelect.value = selectedOption.value;

        if (matches.length === 0) {
            tagHelp.textContent = query ? "No tags match your search." : "No tags available.";
        } else if (!query && matches.length > suggestionLimit) {
            tagHelp.textContent = "Showing common tags. Search to find more.";
        } else {
            tagHelp.textContent = matches.length > suggestionLimit
                ? "Type more to narrow your search."
                : "Choose a tag from the dropdown.";
        }
    }

    tagSearch.hidden = false;
    tagSearch.addEventListener("input", updateTagOptions);
    tagSearch.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === "ArrowDown") {
            event.preventDefault();
            tagSelect.focus();
        }
    });
    tagSelect.addEventListener("change", updateTagOptions);
    updateTagOptions();

    const form = tagSelect.form;
    const startDate = form.elements.start_date;
    const endDate = form.elements.end_date;
    const maxDays = Number(form.dataset.maxDateDays);
    let pendingRequest;

    function updateEndDateBounds() {
        endDate.min = startDate.value > startDate.min && startDate.value <= startDate.max
            ? startDate.value
            : startDate.min;
    }

    async function refreshTags() {
        pendingRequest?.abort();
        endDate.setCustomValidity("");
        tagOptions = [];
        tagSelect.replaceChildren(allTags);

        if (!startDate.value || !endDate.value) {
            tagHelp.textContent = "Enter both dates to see available tags.";
            return;
        }

        if (startDate.value > startDate.max || endDate.value > startDate.max) {
            const message = "Choose dates through today (UTC).";
            endDate.setCustomValidity(message);
            tagHelp.textContent = message;
            return;
        }
        if (startDate.value < startDate.min || endDate.value < startDate.min) {
            const message = `Choose dates within the latest ${maxDays} calendar days (UTC).`;
            endDate.setCustomValidity(message);
            tagHelp.textContent = message;
            return;
        }

        if (endDate.value < startDate.value) {
            const message = "End date must be on or after the start date.";
            endDate.setCustomValidity(message);
            tagHelp.textContent = message;
            return;
        }

        const controller = new AbortController();
        pendingRequest = controller;
        tagHelp.textContent = "Loading tags for these dates…";
        const params = new URLSearchParams({
            start_date: startDate.value,
            end_date: endDate.value,
        });

        try {
            const response = await fetch(`${form.dataset.tagsUrl}?${params}`, {
                signal: controller.signal,
            });
            if (!response.ok) {
                throw new Error("Could not load tags.");
            }
            const { tags, downloaded_at } = await response.json();
            if (controller.signal.aborted) {
                return;
            }
            tagOptions = tags.map((tag) => new Option(tag, tag));
            showSnapshotTime(downloaded_at);
            updateTagOptions();
        } catch {
            if (!controller.signal.aborted) {
                tagHelp.textContent = "Could not load tags. Use Search to retry.";
            }
        }
    }

    startDate.addEventListener("change", () => {
        updateEndDateBounds();
        if (endDate.value && (endDate.value < endDate.min || endDate.value > endDate.max)) {
            endDate.value = "";
        }
        refreshTags();
    });
    endDate.addEventListener("change", refreshTags);
    updateEndDateBounds();
}
