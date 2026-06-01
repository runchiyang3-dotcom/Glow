const calendarGrid = document.querySelector("#calendarGrid");
const calendarMonth = document.querySelector("#calendarMonth");
const dateNote = document.querySelector("#dateNote");
const monthButtons = document.querySelectorAll("[data-month]");
const feedSortButtons = document.querySelectorAll("[data-feed-sort]");
const bookableFilterButtons = document.querySelectorAll("[data-bookable-filter]");
const communityCards = document.querySelectorAll(".community-section [data-latest]");
const communityPageCards = document.querySelectorAll(".community-page .community-feed [data-latest]");
const linkedPostCards = document.querySelectorAll("[data-post-href]");
const cityInput = document.querySelector("#cityInput");
const citySuggestions = document.querySelector("#citySuggestions");
const communityPostForm = document.querySelector("[data-community-post-form]");
const artistRegistrationForm = document.querySelector("[data-artist-registration-form]");
const communityAddressInput = communityPostForm?.querySelector("[name='address']");
const communityAddressSuggestions = document.querySelector("#communityAddressSuggestions");
const manualDateInput = document.querySelector("#manualDateInput");
const hasCalendar = Boolean(calendarGrid && calendarMonth && dateNote && monthButtons.length);
const scheduleSlots = document.querySelectorAll("[data-slot]");
const profileCalendarGrid = document.querySelector("#profileCalendarGrid");
const profileCalendarMonth = document.querySelector("#profileCalendarMonth");
const profileDateNote = document.querySelector("#profileDateNote");
const profileMonthButtons = document.querySelectorAll("[data-profile-month]");
const profilePostCards = document.querySelectorAll("[data-profile-post]");
const profilePostNextButton = document.querySelector("[data-profile-post-next]");
const bookingForm = document.querySelector("#bookingForm");
const bookingDateInput = document.querySelector("#bookingDate");
const bookingTimeInput = document.querySelector("#bookingTime");
const selectedSlotLabel = document.querySelector("#selectedSlotLabel");
const bookingStatus = document.querySelector("#bookingStatus");
const appointmentCards = document.querySelectorAll("[data-appointment-card]");
const appointmentModal = document.querySelector("[data-appointment-modal]");
const canUsePointerParallax = window.matchMedia("(pointer: fine)").matches &&
  !window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const today = new Date();
today.setHours(0, 0, 0, 0);
let visibleYear = today.getFullYear();
let visibleMonth = today.getMonth();
let profileVisibleYear = today.getFullYear();
let profileVisibleMonth = today.getMonth();
const selectedDates = new Set();
let selectedProfileDate = profileCalendarGrid?.dataset.selectedDate || null;
let activeSort = "latest";
let bookableOnly = false;
let profilePostPage = 1;
let communityPageVisibleLimit = Infinity;
let pendingDrift = 0;
let driftFrame = null;
const appointmentProgressByStatus = {
  pending: { completeUntil: 0, current: 1 },
  accepted: { completeUntil: 1, current: 2 },
  deposit_paid: { completeUntil: 2, current: 3 },
  completed: { completeUntil: 3, current: 4 },
  final_paid: { completeUntil: 4, current: null }
};
const australianCities = [
  "Sydney, NSW",
  "Melbourne, VIC",
  "Brisbane, QLD",
  "Perth, WA",
  "Adelaide, SA",
  "Canberra, ACT",
  "Hobart, TAS",
  "Darwin, NT",
  "Gold Coast, QLD",
  "Newcastle, NSW",
  "Wollongong, NSW",
  "Geelong, VIC",
  "Sunshine Coast, QLD",
  "Townsville, QLD",
  "Cairns, QLD",
  "Toowoomba, QLD",
  "Ballarat, VIC",
  "Bendigo, VIC",
  "Launceston, TAS",
  "Albury-Wodonga, NSW/VIC",
  "Mackay, QLD",
  "Rockhampton, QLD",
  "Bunbury, WA",
  "Mandurah, WA",
  "Central Coast, NSW",
  "Blue Mountains, NSW",
  "Coffs Harbour, NSW",
  "Port Macquarie, NSW",
  "Tamworth, NSW",
  "Orange, NSW",
  "Wagga Wagga, NSW",
  "Shepparton, VIC",
  "Mildura, VIC",
  "Alice Springs, NT",
  "Broome, WA"
];
const communityAddressOptions = [
  { label: "CBD studio, Sydney NSW", city: "Sydney, NSW" },
  { label: "Surry Hills studio, Sydney NSW", city: "Sydney, NSW" },
  { label: "Fitzroy studio, Melbourne VIC", city: "Melbourne, VIC" },
  { label: "Southbank artist suite, Melbourne VIC", city: "Melbourne, VIC" },
  { label: "Fortitude Valley studio, Brisbane QLD", city: "Brisbane, QLD" },
  { label: "South Brisbane studio, Brisbane QLD", city: "Brisbane, QLD" },
  { label: "Surfers Paradise mobile service, Gold Coast QLD", city: "Gold Coast, QLD" },
  { label: "Subiaco studio, Perth WA", city: "Perth, WA" },
  { label: "Norwood studio, Adelaide SA", city: "Adelaide, SA" },
  { label: "New Town studio, Hobart TAS", city: "Hobart, TAS" }
];
const trendingTags = [
  { tag: "kpop", count: 301 },
  { tag: "bridal", count: 284 },
  { tag: "soft glam", count: 259 },
  { tag: "glass skin", count: 247 },
  { tag: "douyin", count: 228 },
  { tag: "editorial", count: 193 },
  { tag: "clean girl", count: 182 },
  { tag: "grunge", count: 144 },
  { tag: "latte makeup", count: 137 },
  { tag: "coquette", count: 125 },
  { tag: "y2k", count: 118 },
  { tag: "sunset blush", count: 89 }
];
const artistRegistrationFallbackCities = [...australianCities];
const maxCommunityPosts = 6;
const profilePostPageCount = 2;
const communityPageOrderedCards = [...communityPageCards];
const profileAvailabilityWeekdays = JSON.parse(profileCalendarGrid?.dataset.availabilityWeekdays || "[]");
const profileBookedDates = new Set(JSON.parse(profileCalendarGrid?.dataset.bookedDates || "[]"));
const profileOccupiedDates = new Set(JSON.parse(profileCalendarGrid?.dataset.occupiedDates || "[]"));
const isDashboardProfileCalendar = profileCalendarGrid?.dataset.profileMode === "dashboard";

if (selectedProfileDate) {
  const [selectedYear, selectedMonth] = selectedProfileDate.split("-").map(Number);
  if (selectedYear && selectedMonth) {
    profileVisibleYear = selectedYear;
    profileVisibleMonth = selectedMonth - 1;
  }
}

function getProfileAvailability(year, month, day) {
  const key = dateKey(year, month, day);
  const date = new Date(year, month, day);
  const jsWeekday = date.getDay();
  const weekday = jsWeekday === 0 ? 6 : jsWeekday - 1;

  if (profileBookedDates.has(key)) {
    return "booked";
  }

  if (profileOccupiedDates.has(key)) {
    return "unavailable";
  }

  if (profileAvailabilityWeekdays.length) {
    return profileAvailabilityWeekdays.includes(weekday) ? "available" : "unavailable";
  }

  if (isDashboardProfileCalendar) {
    return "available";
  }

  if (jsWeekday === 0) {
    return "unavailable";
  }

  if ([3, 9, 14, 18, 24, 29].includes(day)) {
    return "booked";
  }

  if (jsWeekday === 1 || jsWeekday === 6 || day % 5 === 0) {
    return "available";
  }

  return "unavailable";
}

function formatProfileDate(key) {
  const [year, month, day] = key.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-AU", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric"
  });
}

function resetBookingTimeInput() {
  if (!bookingTimeInput) {
    return;
  }

  bookingTimeInput.value = "";
}

function setBookingDateValue(key) {
  if (!bookingDateInput) {
    return;
  }

  bookingDateInput.value = bookingDateInput.type === "date" ? key : formatProfileDate(key);
}

function setBookingTimeValue(time) {
  if (!bookingTimeInput) {
    return;
  }

  bookingTimeInput.value = time;
}

function dateKey(year, month, day) {
  return `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function formatSelectedDates() {
  if (selectedDates.size === 0) {
    return "Select one or more possible dates, or type a date above.";
  }

  const dates = [...selectedDates]
    .sort()
    .map((key) => {
      const [year, month, day] = key.split("-").map(Number);
      return new Date(year, month - 1, day).toLocaleDateString("en-AU", {
        day: "numeric",
        month: "short"
      });
    });

  return `Possible dates: ${dates.join(", ")}`;
}

function syncManualDateInput() {
  if (!manualDateInput) {
    return;
  }

  if (selectedDates.size === 0) {
    manualDateInput.value = "";
    return;
  }

  manualDateInput.value = [...selectedDates].sort()[0];
}

function renderCalendar() {
  if (!hasCalendar) {
    return;
  }

  const firstDay = new Date(visibleYear, visibleMonth, 1);
  const daysInMonth = new Date(visibleYear, visibleMonth + 1, 0).getDate();
  const mondayFirstOffset = (firstDay.getDay() + 6) % 7;

  calendarMonth.textContent = firstDay.toLocaleDateString("en-AU", {
    month: "long",
    year: "numeric"
  });

  calendarGrid.innerHTML = "";

  for (let i = 0; i < mondayFirstOffset; i += 1) {
    const empty = document.createElement("span");
    empty.className = "calendar-day is-empty";
    calendarGrid.append(empty);
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    const key = dateKey(visibleYear, visibleMonth, day);
    const date = new Date(visibleYear, visibleMonth, day);
    const isPast = date < today;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "calendar-day";
    button.textContent = day;
    button.setAttribute("aria-pressed", selectedDates.has(key) ? "true" : "false");
    button.setAttribute("aria-label", `Toggle ${key} as a possible makeup date`);

    if (
      visibleYear === today.getFullYear() &&
      visibleMonth === today.getMonth() &&
      day === today.getDate()
    ) {
      button.classList.add("is-today");
    }

    if (isPast) {
      selectedDates.delete(key);
      button.classList.add("is-past");
      button.disabled = true;
      button.setAttribute("aria-label", `${key} is no longer available for booking`);
      button.setAttribute("aria-disabled", "true");
    }

    if (selectedDates.has(key)) {
      button.classList.add("is-selected");
    }

    button.addEventListener("click", () => {
      if (isPast) {
        return;
      }

      if (selectedDates.has(key)) {
        selectedDates.delete(key);
      } else {
        selectedDates.add(key);
      }
      dateNote.textContent = formatSelectedDates();
      renderCalendar();
    });

    calendarGrid.append(button);
  }

  syncManualDateInput();
}

if (hasCalendar) {
  monthButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const direction = button.dataset.month === "next" ? 1 : -1;
      visibleMonth += direction;

      if (visibleMonth > 11) {
        visibleMonth = 0;
        visibleYear += 1;
      }

      if (visibleMonth < 0) {
        visibleMonth = 11;
        visibleYear -= 1;
      }

      renderCalendar();
    });
  });
}

if (manualDateInput && hasCalendar) {
  const applyManualDate = () => {
    const value = manualDateInput.value;

    if (!value) {
      selectedDates.clear();
      dateNote.textContent = formatSelectedDates();
      renderCalendar();
      return;
    }

    const [year, month, day] = value.split("-").map(Number);
    const chosenDate = new Date(year, month - 1, day);

    if (Number.isNaN(chosenDate.getTime()) || chosenDate < today) {
      return;
    }

    selectedDates.clear();
    selectedDates.add(value);
    visibleYear = year;
    visibleMonth = month - 1;
    dateNote.textContent = formatSelectedDates();
    renderCalendar();
  };

  manualDateInput.addEventListener("change", applyManualDate);
  manualDateInput.addEventListener("input", applyManualDate);
}

function renderCommunityFeed() {
  if (!communityCards.length) {
    return;
  }

  const sortedCards = [...communityCards].sort((a, b) => {
    const first = Number(a.dataset[activeSort]);
    const second = Number(b.dataset[activeSort]);
    return second - first;
  });

  let visibleIndex = 0;

  sortedCards.forEach((card, index) => {
    const shouldShow = !bookableOnly || card.dataset.bookable === "true";
    const withinLimit = visibleIndex < maxCommunityPosts;
    card.hidden = !shouldShow || !withinLimit;

    if (shouldShow) {
      visibleIndex += 1;
    }

    card.style.setProperty("--delay", `${index * 55}ms`);
    card.parentElement.append(card);
  });
}

function renderCommunityPageFeed() {
  if (!communityPageCards.length) {
    return;
  }

  const sortedCards = [...communityPageOrderedCards].sort((a, b) => {
    const first = Number(a.dataset[activeSort]);
    const second = Number(b.dataset[activeSort]);
    return second - first;
  });
  let visibleIndex = 0;

  sortedCards.forEach((card, index) => {
    const shouldShow = !bookableOnly || card.dataset.bookable === "true";
    const withinLimit = visibleIndex < communityPageVisibleLimit;
    card.hidden = !shouldShow || !withinLimit;

    if (shouldShow) {
      visibleIndex += 1;
    }

    card.style.setProperty("--delay", `${index * 55}ms`);
    card.parentElement.append(card);
  });
}

function setBookableFilter(filter) {
  bookableOnly = filter === "bookable";
  bookableFilterButtons.forEach((item) => {
    const isActive = item.dataset.bookableFilter === filter;
    item.classList.toggle("is-active", isActive);
    item.setAttribute("aria-pressed", isActive ? "true" : "false");
  });
  renderCommunityFeed();
  renderCommunityPageFeed();
}

window.setBookableFilter = setBookableFilter;

feedSortButtons.forEach((button) => {
  button.addEventListener("click", () => {
    activeSort = button.dataset.feedSort;

    feedSortButtons.forEach((item) => {
      item.classList.toggle("is-active", item === button);
      item.setAttribute("aria-pressed", item === button ? "true" : "false");
    });

    renderCommunityFeed();
    renderCommunityPageFeed();
  });
});

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-bookable-filter]");

  if (!button) {
    return;
  }

  setBookableFilter(button.dataset.bookableFilter);
});

document.addEventListener("pointerdown", (event) => {
  const button = event.target.closest("[data-bookable-filter]");

  if (!button) {
    return;
  }

  setBookableFilter(button.dataset.bookableFilter);
});

if (communityPageCards.length) {
  const communityPageSentinel = document.querySelector(".community-more-auto");
  if (communityPageSentinel) {
    communityPageSentinel.hidden = true;
  }

  renderCommunityPageFeed();
}

linkedPostCards.forEach((card) => {
  card.addEventListener("click", (event) => {
    if (event.target.closest("a, button, input, select, textarea")) {
      return;
    }

    window.location.href = card.dataset.postHref;
  });

  card.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    event.preventDefault();
    window.location.href = card.dataset.postHref;
  });
});

function renderProfilePosts() {
  if (!profilePostCards.length) {
    return;
  }

  profilePostCards.forEach((card, index) => {
    card.hidden = Number(card.dataset.page) !== profilePostPage;
    card.style.setProperty("--delay", `${index * 55}ms`);
  });

  if (profilePostNextButton) {
    profilePostNextButton.setAttribute(
      "aria-label",
      profilePostPage === profilePostPageCount ? "First page" : "Next page"
    );
  }
}

if (profilePostNextButton) {
  profilePostNextButton.addEventListener("click", () => {
    profilePostPage = profilePostPage === profilePostPageCount ? 1 : profilePostPage + 1;
    renderProfilePosts();
  });
}

function renderProfileCalendar() {
  if (!profileCalendarGrid || !profileCalendarMonth || !profileDateNote) {
    return;
  }

  const firstDay = new Date(profileVisibleYear, profileVisibleMonth, 1);
  const daysInMonth = new Date(profileVisibleYear, profileVisibleMonth + 1, 0).getDate();
  const mondayFirstOffset = (firstDay.getDay() + 6) % 7;

  profileCalendarMonth.textContent = firstDay.toLocaleDateString("en-AU", {
    month: "long",
    year: "numeric"
  });

  profileCalendarGrid.innerHTML = "";

  for (let i = 0; i < mondayFirstOffset; i += 1) {
    const empty = document.createElement("span");
    empty.className = "calendar-day is-empty";
    profileCalendarGrid.append(empty);
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    const key = dateKey(profileVisibleYear, profileVisibleMonth, day);
    const status = getProfileAvailability(profileVisibleYear, profileVisibleMonth, day);
    const date = new Date(profileVisibleYear, profileVisibleMonth, day);
    const isPast = date < today;
    const button = document.createElement("button");
    button.type = "button";
    button.className = `calendar-day profile-calendar-day is-${status}`;
    button.dataset.status = status;
    button.dataset.date = key;
    button.innerHTML = `<span class="profile-day-number">${day}</span><span class="profile-day-status">${status}</span>`;
    button.setAttribute("aria-pressed", selectedProfileDate === key ? "true" : "false");
    button.setAttribute("aria-label", `${key} is ${status}`);

    if (
      profileVisibleYear === today.getFullYear() &&
      profileVisibleMonth === today.getMonth() &&
      day === today.getDate()
    ) {
      button.classList.add("is-today");
    }

    if (isPast) {
      button.classList.add("is-past");
      button.disabled = true;
      button.setAttribute("aria-disabled", "true");
    }

      if (status !== "available" && !isDashboardProfileCalendar) {
        button.disabled = true;
        button.setAttribute("aria-disabled", "true");
      }

    if (selectedProfileDate === key) {
      button.classList.add("is-selected");
    }

      button.addEventListener("click", () => {
        if (isPast) {
          return;
        }

        if (isDashboardProfileCalendar) {
          const baseUrl = profileCalendarGrid.dataset.profileSelectedUrl || window.location.pathname;
          window.location.href = `${baseUrl}?date=${key}`;
          return;
        }

        if (status !== "available") {
          return;
        }

      selectedProfileDate = key;
      profileDateNote.textContent = `Selected date: ${formatProfileDate(key)}`;

      if (selectedSlotLabel) {
        selectedSlotLabel.textContent = formatProfileDate(key);
      }

      if (bookingDateInput) {
        setBookingDateValue(key);
      }

      if (bookingTimeInput) {
        resetBookingTimeInput();
      }

      if (bookingStatus) {
        bookingStatus.textContent = "";
      }

      renderProfileCalendar();
    });

    profileCalendarGrid.append(button);
  }
}

profileMonthButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const direction = button.dataset.profileMonth === "next" ? 1 : -1;
    profileVisibleMonth += direction;

    if (profileVisibleMonth > 11) {
      profileVisibleMonth = 0;
      profileVisibleYear += 1;
    }

    if (profileVisibleMonth < 0) {
      profileVisibleMonth = 11;
      profileVisibleYear -= 1;
    }

    renderProfileCalendar();
  });
});

function setupAutocomplete({ input, list, source, onSelect }) {
  if (!input || !list) {
    return;
  }

  const hideSuggestions = () => {
    list.hidden = true;
    list.innerHTML = "";
    input.setAttribute("aria-expanded", "false");
  };

  const renderSuggestions = () => {
    const query = input.value.trim().toLowerCase();
    const matches = source(query).slice(0, 8);

    list.innerHTML = "";

    matches.forEach((item) => {
      const option = document.createElement("button");
      option.type = "button";
      option.className = "city-suggestion";
      option.setAttribute("role", "option");
      option.textContent = item.label;
      option.addEventListener("pointerdown", (event) => {
        event.preventDefault();
        input.value = item.label;
        onSelect(item);
        hideSuggestions();
      });
      list.append(option);
    });

    list.hidden = matches.length === 0;
    input.setAttribute("aria-expanded", matches.length > 0 ? "true" : "false");
  };

  hideSuggestions();
  input.addEventListener("focus", renderSuggestions);
  input.addEventListener("input", renderSuggestions);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      hideSuggestions();
    }
  });

  document.addEventListener("pointerdown", (event) => {
    if (!input.contains(event.target) && !list.contains(event.target)) {
      hideSuggestions();
    }
  });
}

setupAutocomplete({
  input: cityInput,
  list: citySuggestions,
  source: (query) => australianCities
    .filter((city) => city.toLowerCase().includes(query))
    .map((city) => ({ label: city })),
  onSelect: () => {}
});

function getAddressComponent(place, types) {
  const components = place?.address_components || [];
  for (const type of types) {
    const component = components.find((item) => item.types.includes(type));
    if (component) {
      return component.long_name || component.short_name || "";
    }
  }
  return "";
}

function initArtistRegistrationAutocomplete() {
  if (!artistRegistrationForm) {
    return;
  }

  if (artistRegistrationForm.dataset.registrationInitialized === "true") {
    return;
  }
  artistRegistrationForm.dataset.registrationInitialized = "true";

  const addressInput = artistRegistrationForm.querySelector("[data-registration-address-input]");
  const addressSuggestions = artistRegistrationForm.querySelector("[data-registration-address-suggestions]");
  const hiddenLocation = artistRegistrationForm.querySelector("[data-registration-location]");
  const hiddenCity = artistRegistrationForm.querySelector("[data-registration-city]");
  const hiddenTags = artistRegistrationForm.querySelector("[data-registration-tags]");
  const tagComposer = artistRegistrationForm.querySelector("[data-registration-tag-composer]");
  const tagInput = artistRegistrationForm.querySelector("[data-registration-tag-input]");
  const tagAddButton = artistRegistrationForm.querySelector("[data-registration-tag-add]");
  const tagList = artistRegistrationForm.querySelector("[data-registration-tag-list]");
  const tagSuggestions = artistRegistrationForm.querySelector("[data-registration-tag-suggestions]");

  if (!addressInput || !hiddenLocation || !hiddenCity || !hiddenTags) {
    return;
  }

  const syncTags = (activeTags) => {
    hiddenTags.value = activeTags.join(", ");
    if (tagInput) {
      tagInput.setCustomValidity("");
    }
    if (!tagList) {
      return;
    }

    tagList.innerHTML = "";
    activeTags.forEach((tag) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "tag-chip";
      chip.textContent = tag;
      chip.addEventListener("click", () => {
        syncTags(activeTags.filter((item) => item !== tag));
      });
      tagList.append(chip);
    });
  };

  let activeTags = (hiddenTags.value || "")
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
  syncTags(activeTags);

  const hideTagSuggestions = () => {
    if (!tagSuggestions) {
      return;
    }
    tagSuggestions.hidden = true;
    tagSuggestions.innerHTML = "";
  };

  const addTag = (rawTag) => {
    const tag = rawTag.trim().replace(/\s+/g, " ");
    if (!tag) {
      return;
    }

    if (activeTags.some((item) => item.toLowerCase() === tag.toLowerCase())) {
      if (tagInput) {
        tagInput.value = "";
        tagInput.setCustomValidity("");
      }
      hideTagSuggestions();
      return;
    }

    activeTags = [...activeTags, tag];
    syncTags(activeTags);
    if (tagInput) {
      tagInput.value = "";
      tagInput.setCustomValidity("");
    }
    hideTagSuggestions();
  };

  const renderTagSuggestions = () => {
    if (!tagSuggestions || !tagInput) {
      return;
    }

    const query = tagInput.value.trim().toLowerCase();
    if (!query) {
      hideTagSuggestions();
      return;
    }

    const matches = trendingTags
      .filter((item) => item.tag.toLowerCase().includes(query) && !activeTags.some((tag) => tag.toLowerCase() === item.tag))
      .slice(0, 6);

    tagSuggestions.innerHTML = "";
    matches.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "tag-suggestion";
      button.innerHTML = `<strong>${item.tag}</strong><span>${item.count} discussions</span>`;
      button.addEventListener("pointerdown", (event) => {
        event.preventDefault();
        addTag(item.tag);
      });
      tagSuggestions.append(button);
    });

    tagSuggestions.hidden = matches.length === 0;
  };

  if (tagInput) {
    tagInput.addEventListener("input", renderTagSuggestions);
    tagInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === ",") {
        event.preventDefault();
        addTag(tagInput.value);
      }

      if (event.key === "Escape") {
        hideTagSuggestions();
      }
    });
  }

  if (tagAddButton && tagInput) {
    tagAddButton.addEventListener("click", () => addTag(tagInput.value));
  }

  if (tagComposer) {
    document.addEventListener("pointerdown", (event) => {
      if (!tagComposer.contains(event.target)) {
        hideTagSuggestions();
      }
    });
  }

  if (window.google?.maps?.places?.Autocomplete) {
    const autocomplete = new google.maps.places.Autocomplete(addressInput, {
      componentRestrictions: { country: "au" },
      fields: ["address_components", "formatted_address", "name", "place_id"],
      types: ["(cities)"],
    });

    autocomplete.addListener("place_changed", () => {
      const place = autocomplete.getPlace();
      const formattedAddress = place.formatted_address || place.name || addressInput.value.trim();
      const cityLabel = place.name || formattedAddress;
      hiddenLocation.value = cityLabel;
      hiddenCity.value =
        getAddressComponent(place, ["locality", "postal_town", "administrative_area_level_2", "administrative_area_level_1"]) ||
        cityLabel ||
        hiddenCity.value ||
        "";
      addressInput.value = cityLabel;
      addressInput.setCustomValidity("");
      addressInput.dispatchEvent(new Event("input", { bubbles: true }));
    });
  } else if (addressInput && hiddenLocation) {
    const renderAddressSuggestions = () => {
      if (!addressSuggestions) {
        return;
      }

      const query = addressInput.value.trim().toLowerCase();
      const matches = artistRegistrationFallbackCities
        .filter((city) => city.toLowerCase().includes(query))
        .slice(0, 6);

      addressSuggestions.innerHTML = "";
      matches.forEach((city) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "city-suggestion";
        button.textContent = city;
        button.addEventListener("pointerdown", (event) => {
          event.preventDefault();
          addressInput.value = city;
          hiddenLocation.value = city;
          hiddenCity.value = city;
          addressSuggestions.hidden = true;
        });
        addressSuggestions.append(button);
      });

      addressSuggestions.hidden = matches.length === 0;
    };

    addressInput.addEventListener("input", () => {
      hiddenLocation.value = "";
      hiddenCity.value = "";
      addressInput.setCustomValidity("");
      renderAddressSuggestions();
    });

    addressInput.addEventListener("focus", renderAddressSuggestions);
    document.addEventListener("pointerdown", (event) => {
      if (!addressInput.contains(event.target) && !addressSuggestions?.contains(event.target)) {
        if (addressSuggestions) {
          addressSuggestions.hidden = true;
        }
      }
    });
  }

  artistRegistrationForm.addEventListener("submit", (event) => {
    if (!hiddenLocation.value.trim()) {
      if (!window.google?.maps?.places?.Autocomplete && addressInput.value.trim()) {
        hiddenLocation.value = addressInput.value.trim();
      }
    }

    if (!hiddenLocation.value.trim()) {
      event.preventDefault();
      addressInput.setCustomValidity("Choose a city from the suggestions.");
      addressInput.reportValidity();
      return;
    }

    if (!hiddenTags.value.trim()) {
      event.preventDefault();
      if (tagInput) {
        tagInput.setCustomValidity("Add at least one style tag.");
        tagInput.reportValidity();
      }
    }
  });

  // Ensure the form keeps the selected address visible after validation errors.
  if (addressInput.value.trim() && hiddenLocation.value && !window.google?.maps?.places?.Autocomplete) {
    hiddenLocation.value = addressInput.value.trim();
  }

  // Basic local fallback suggestions when the API key isn't configured.
  if (!window.google?.maps?.places?.Autocomplete && tagInput && tagSuggestions) {
    tagInput.setAttribute("placeholder", "Clean beauty, bridal glow, soft glam");
  }
}

window.initArtistRegistrationAutocomplete = initArtistRegistrationAutocomplete;

if (artistRegistrationForm) {
  initArtistRegistrationAutocomplete();
}

if (communityPostForm) {
  const bookableInput = communityPostForm.querySelector("[name='is_bookable']");
  const bookableChoices = communityPostForm.querySelectorAll("[data-bookable-choice]");
  const bookableFields = communityPostForm.querySelector("[data-bookable-fields]");
  const derivedCityInput = communityPostForm.querySelector("[name='derived_city']");
  const tagComposer = communityPostForm.querySelector("[data-tag-composer]");
  const tagInput = communityPostForm.querySelector("[data-tag-input]");
  const tagList = communityPostForm.querySelector("[data-tag-list]");
  const tagSuggestions = communityPostForm.querySelector("[data-tag-suggestions]");
  const styleTagsInput = communityPostForm.querySelector("[name='style_tags']");
  const imageComposer = communityPostForm.querySelector("[data-image-composer]");
  const fileInput = communityPostForm.querySelector("[name='image']");
  const dropzone = communityPostForm.querySelector("[data-image-dropzone]");
  const cropWorkspace = communityPostForm.querySelector("[data-crop-workspace]");
  const cropFrame = communityPostForm.querySelector("[data-crop-frame]");
  const cropImage = communityPostForm.querySelector("[data-crop-image]");
  const cropZoom = communityPostForm.querySelector("[data-crop-zoom]");
  const cropLeftInput = communityPostForm.querySelector("[name='crop_left']");
  const cropTopInput = communityPostForm.querySelector("[name='crop_top']");
  const cropWidthInput = communityPostForm.querySelector("[name='crop_width']");
  const cropHeightInput = communityPostForm.querySelector("[name='crop_height']");
  let activeTags = (styleTagsInput?.value || "")
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
  let imageState = null;

  const renderBookableState = () => {
    const isBookable = bookableInput?.value === "true";
    bookableChoices.forEach((button) => {
      const active = button.dataset.bookableChoice === String(isBookable);
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });

    if (bookableFields) {
      bookableFields.hidden = !isBookable;
    }
  };

  bookableChoices.forEach((button) => {
    button.addEventListener("click", () => {
      if (!bookableInput) {
        return;
      }
      bookableInput.value = button.dataset.bookableChoice;
      renderBookableState();
    });
  });
  renderBookableState();

  setupAutocomplete({
    input: communityAddressInput,
    list: communityAddressSuggestions,
    source: (query) => communityAddressOptions.filter((item) => item.label.toLowerCase().includes(query)),
    onSelect: (item) => {
      if (derivedCityInput) {
        derivedCityInput.value = item.city;
      }
    }
  });

  if (communityAddressInput && derivedCityInput) {
    communityAddressInput.addEventListener("input", () => {
      const rawValue = communityAddressInput.value.trim();
      const matchedOption = communityAddressOptions.find((item) => item.label === rawValue);
      if (matchedOption) {
        derivedCityInput.value = matchedOption.city;
        return;
      }

      const matchedCity = australianCities.find((city) => rawValue.toLowerCase().includes(city.split(",")[0].toLowerCase()));
      derivedCityInput.value = matchedCity || "";
    });
  }

  const syncTags = () => {
    if (styleTagsInput) {
      styleTagsInput.value = activeTags.join(", ");
    }

    if (!tagList) {
      return;
    }

    tagList.innerHTML = "";
    activeTags.forEach((tag) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "tag-chip";
      chip.textContent = tag;
      chip.addEventListener("click", () => {
        activeTags = activeTags.filter((item) => item !== tag);
        syncTags();
      });
      tagList.append(chip);
    });
  };

  const hideTagSuggestions = () => {
    if (!tagSuggestions) {
      return;
    }
    tagSuggestions.hidden = true;
    tagSuggestions.innerHTML = "";
  };

  const addTag = (rawTag) => {
    const tag = rawTag.trim().replace(/\s+/g, " ");
    if (!tag) {
      return;
    }
    const alreadyExists = activeTags.some((item) => item.toLowerCase() === tag.toLowerCase());
    if (alreadyExists) {
      tagInput.value = "";
      hideTagSuggestions();
      return;
    }
    activeTags = [...activeTags, tag];
    tagInput.value = "";
    syncTags();
    hideTagSuggestions();
  };

  if (tagComposer && tagInput && tagSuggestions) {
    syncTags();

    const renderTagSuggestions = () => {
      const query = tagInput.value.trim().toLowerCase();
      if (!query) {
        hideTagSuggestions();
        return;
      }

      const matches = trendingTags
        .filter((item) => item.tag.toLowerCase().includes(query) && !activeTags.some((tag) => tag.toLowerCase() === item.tag))
        .slice(0, 6);

      tagSuggestions.innerHTML = "";
      matches.forEach((item) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "tag-suggestion";
        button.innerHTML = `<strong>${item.tag}</strong><span>${item.count} discussions</span>`;
        button.addEventListener("pointerdown", (event) => {
          event.preventDefault();
          addTag(item.tag);
        });
        tagSuggestions.append(button);
      });

      tagSuggestions.hidden = matches.length === 0;
    };

    tagInput.addEventListener("input", renderTagSuggestions);
    tagInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === ",") {
        event.preventDefault();
        addTag(tagInput.value);
      }
      if (event.key === "Backspace" && !tagInput.value && activeTags.length) {
        activeTags = activeTags.slice(0, -1);
        syncTags();
      }
      if (event.key === "Escape") {
        hideTagSuggestions();
      }
    });
    document.addEventListener("pointerdown", (event) => {
      if (!tagComposer.contains(event.target)) {
        hideTagSuggestions();
      }
    });
  }

  const updateCropFields = () => {
    if (!imageState || !cropFrame || !cropImage) {
      return;
    }

    const frameRect = cropFrame.getBoundingClientRect();
    const frameWidth = frameRect.width;
    const frameHeight = frameRect.height;
    const displayWidth = imageState.naturalWidth * imageState.scale;
    const displayHeight = imageState.naturalHeight * imageState.scale;
    const imageLeft = (frameWidth - displayWidth) / 2 + imageState.offsetX;
    const imageTop = (frameHeight - displayHeight) / 2 + imageState.offsetY;
    const left = Math.max(0, Math.min(imageState.naturalWidth, -imageLeft / imageState.scale));
    const top = Math.max(0, Math.min(imageState.naturalHeight, -imageTop / imageState.scale));
    const right = Math.max(left + 1, Math.min(imageState.naturalWidth, (frameWidth - imageLeft) / imageState.scale));
    const bottom = Math.max(top + 1, Math.min(imageState.naturalHeight, (frameHeight - imageTop) / imageState.scale));

    cropLeftInput.value = left.toFixed(2);
    cropTopInput.value = top.toFixed(2);
    cropWidthInput.value = (right - left).toFixed(2);
    cropHeightInput.value = (bottom - top).toFixed(2);
  };

  const renderCrop = () => {
    if (!imageState || !cropImage || !cropFrame) {
      return;
    }

    const frameRect = cropFrame.getBoundingClientRect();
    const frameWidth = frameRect.width;
    const frameHeight = frameRect.height;
    const maxX = Math.max(0, (imageState.naturalWidth * imageState.scale - frameWidth) / 2);
    const maxY = Math.max(0, (imageState.naturalHeight * imageState.scale - frameHeight) / 2);
    imageState.offsetX = Math.min(maxX, Math.max(-maxX, imageState.offsetX));
    imageState.offsetY = Math.min(maxY, Math.max(-maxY, imageState.offsetY));
    cropImage.style.width = `${imageState.naturalWidth * imageState.baseScale}px`;
    cropImage.style.height = `${imageState.naturalHeight * imageState.baseScale}px`;
    cropImage.style.transform = `translate(${imageState.offsetX}px, ${imageState.offsetY}px) scale(${imageState.renderScale})`;
    updateCropFields();
  };

  const loadComposerImage = (file) => {
    if (!file || !file.type.startsWith("image/")) {
      return;
    }

    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    fileInput.files = dataTransfer.files;

    const reader = new FileReader();
    reader.addEventListener("load", () => {
      cropImage.src = reader.result;
      cropWorkspace.hidden = false;

      const previewImage = new Image();
      previewImage.onload = () => {
        const frameWidth = cropFrame.clientWidth || 320;
        const frameHeight = cropFrame.clientHeight || 400;
        const baseScale = Math.max(frameWidth / previewImage.naturalWidth, frameHeight / previewImage.naturalHeight);
        imageState = {
          naturalWidth: previewImage.naturalWidth,
          naturalHeight: previewImage.naturalHeight,
          baseScale,
          scale: baseScale,
          renderScale: 1,
          offsetX: 0,
          offsetY: 0
        };
        cropZoom.value = "1";
        renderCrop();
      };
      previewImage.src = reader.result;
    });
    reader.readAsDataURL(file);
  };

  if (imageComposer && dropzone && fileInput && cropFrame && cropImage && cropZoom) {
    fileInput.addEventListener("change", () => {
      const file = fileInput.files?.[0];
      if (file) {
        loadComposerImage(file);
      }
    });

    dropzone.addEventListener("click", () => fileInput.click());
    dropzone.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        fileInput.click();
      }
    });

    ["dragenter", "dragover"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropzone.classList.add("is-active");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropzone.classList.remove("is-active");
      });
    });

    dropzone.addEventListener("drop", (event) => {
      const file = event.dataTransfer?.files?.[0];
      if (file) {
        loadComposerImage(file);
      }
    });

    communityPostForm.addEventListener("paste", (event) => {
      const imageItem = [...(event.clipboardData?.items || [])].find((item) => item.type.startsWith("image/"));
      if (!imageItem) {
        return;
      }
      event.preventDefault();
      const file = imageItem.getAsFile();
      if (file) {
        loadComposerImage(file);
      }
    });

    cropZoom.addEventListener("input", () => {
      if (!imageState) {
        return;
      }
      imageState.scale = imageState.baseScale * Number(cropZoom.value);
      imageState.renderScale = imageState.scale / imageState.baseScale;
      renderCrop();
    });

    let pointerState = null;
    cropFrame.addEventListener("pointerdown", (event) => {
      if (!imageState) {
        return;
      }
      pointerState = {
        x: event.clientX,
        y: event.clientY,
        offsetX: imageState.offsetX,
        offsetY: imageState.offsetY
      };
      cropFrame.setPointerCapture(event.pointerId);
    });

    cropFrame.addEventListener("pointermove", (event) => {
      if (!pointerState || !imageState) {
        return;
      }
      imageState.offsetX = pointerState.offsetX + (event.clientX - pointerState.x);
      imageState.offsetY = pointerState.offsetY + (event.clientY - pointerState.y);
      renderCrop();
    });

    ["pointerup", "pointercancel", "pointerleave"].forEach((eventName) => {
      cropFrame.addEventListener(eventName, () => {
        pointerState = null;
      });
    });

    window.addEventListener("resize", () => {
      if (imageState) {
        renderCrop();
      }
    });
  }
}

if (canUsePointerParallax) {
  window.addEventListener("pointermove", (event) => {
    const midpoint = window.innerWidth / 2;
    pendingDrift = ((event.clientX - midpoint) / midpoint) * 18;

    if (driftFrame) {
      return;
    }

    driftFrame = window.requestAnimationFrame(() => {
      document.documentElement.style.setProperty("--makeup-drift", `${pendingDrift.toFixed(2)}px`);
      document.documentElement.style.setProperty("--makeup-drift-soft", `${(pendingDrift * 0.55).toFixed(2)}px`);
      document.documentElement.style.setProperty("--makeup-drift-reverse", `${(pendingDrift * -0.45).toFixed(2)}px`);
      document.documentElement.style.setProperty("--makeup-drift-reverse-strong", `${(pendingDrift * -0.7).toFixed(2)}px`);
      driftFrame = null;
    });
  });
}

if (scheduleSlots.length && bookingForm && bookingDateInput && bookingTimeInput && selectedSlotLabel && bookingStatus) {
  const availableSlots = [...scheduleSlots].filter((slot) => slot.dataset.status === "available");
  let activeSlot = null;

  const updateBookingSummary = () => {
    if (!activeSlot) {
      selectedSlotLabel.textContent = "No date selected yet.";
      bookingDateInput.value = "";
      resetBookingTimeInput();
      return;
    }

    selectedSlotLabel.textContent = `${activeSlot.dataset.day}, ${activeSlot.dataset.date} at ${activeSlot.dataset.time}`;
    bookingDateInput.value = activeSlot.dataset.date;
    setBookingTimeValue(activeSlot.dataset.time);
  };

  availableSlots.forEach((slot) => {
    slot.addEventListener("click", () => {
      if (activeSlot) {
        activeSlot.classList.remove("is-selected");
      }

      activeSlot = slot;
      activeSlot.classList.add("is-selected");
      bookingStatus.textContent = "";
      updateBookingSummary();
    });
  });

  bookingForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!activeSlot) {
      bookingStatus.textContent = "Select an available time slot before submitting.";
      return;
    }

    bookingStatus.textContent = `Request sent for ${activeSlot.dataset.day} ${activeSlot.dataset.date} at ${activeSlot.dataset.time}.`;
  });

  updateBookingSummary();
}

if (!scheduleSlots.length && profileCalendarGrid && bookingForm && bookingDateInput && bookingTimeInput && bookingStatus) {
  resetBookingTimeInput();

  bookingForm.addEventListener("submit", (event) => {
    const postsToServer = bookingForm.getAttribute("method")?.toLowerCase() === "post" && bookingForm.getAttribute("action");

    if (!selectedProfileDate) {
      event.preventDefault();
      bookingStatus.textContent = "Select an available date before submitting.";
      return;
    }

    if (!bookingTimeInput.value.trim()) {
      event.preventDefault();
      bookingStatus.textContent = "Enter the time you want the makeup finished.";
      return;
    }

    if (postsToServer) {
      return;
    }

    event.preventDefault();
    bookingStatus.textContent = `Request sent for ${formatProfileDate(selectedProfileDate)}. Finish time: ${bookingTimeInput.value.trim()}.`;
  });
}

function setAppointmentModalText(selector, value) {
  if (!appointmentModal) {
    return;
  }

  const element = appointmentModal.querySelector(selector);
  if (element) {
    element.textContent = value || "";
  }
}

function openAppointmentModal(card) {
  if (!appointmentModal) {
    return;
  }

  const data = card.dataset;
  const avatar = appointmentModal.querySelector("[data-appointment-avatar]");

  if (avatar) {
    avatar.src = data.avatar || "";
    avatar.alt = `${data.person || "Booking contact"} avatar`;
  }

  setAppointmentModalText("[data-appointment-role]", data.role);
  setAppointmentModalText("[data-appointment-person]", data.person);
  setAppointmentModalText("[data-appointment-person-id]", data.personId);
  setAppointmentModalText("[data-appointment-title]", data.title);
  setAppointmentModalText("[data-appointment-time]", `${data.date} - finish by ${data.time}`);
  setAppointmentModalText("[data-appointment-status]", data.status);
  setAppointmentModalText("[data-appointment-full-price]", data.fullPrice);
  setAppointmentModalText("[data-appointment-deposit]", data.deposit);
  setAppointmentModalText("[data-appointment-final]", data.final);
  setAppointmentModalText("[data-appointment-created]", data.created);
  setAppointmentModalText("[data-appointment-address]", data.address);
  setAppointmentModalText("[data-appointment-notes]", data.notes);

  const progress = appointmentProgressByStatus[data.step] || { completeUntil: -1, current: null };
  appointmentModal.querySelectorAll("[data-process-step]").forEach((step, index) => {
    const isComplete = index <= progress.completeUntil;
    const isCurrent = progress.current === index;
    step.classList.toggle("is-complete", isComplete);
    step.classList.toggle("is-current", isCurrent);
    step.classList.toggle("is-pending-step", !isComplete && !isCurrent);
  });

  appointmentModal.hidden = false;
  document.body.classList.add("modal-open");
}

function closeAppointmentModal() {
  if (!appointmentModal) {
    return;
  }

  appointmentModal.hidden = true;
  document.body.classList.remove("modal-open");
}

appointmentCards.forEach((card) => {
  card.addEventListener("click", (event) => {
    if (event.target.closest("a, button, input, select, textarea, form")) {
      return;
    }

    openAppointmentModal(card);
  });

  card.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    if (event.target.closest("a, button, input, select, textarea, form")) {
      return;
    }

    event.preventDefault();
    openAppointmentModal(card);
  });
});

if (appointmentModal) {
  appointmentModal.querySelectorAll("[data-appointment-close]").forEach((button) => {
    button.addEventListener("click", closeAppointmentModal);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !appointmentModal.hidden) {
      closeAppointmentModal();
    }
  });
}

renderCalendar();
renderCommunityFeed();
renderProfilePosts();
renderProfileCalendar();
