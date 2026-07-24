"use strict";

const timezoneInput = document.getElementById("timezone_hint");
const languageInput = document.getElementById("language_hint");

if (timezoneInput) {
  timezoneInput.value = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
}
if (languageInput) {
  languageInput.value = navigator.language || "";
}
