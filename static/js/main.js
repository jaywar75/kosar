// static/js/main.js

(() => {
  // 1. Dynamically load the Bootstrap 5 JS Bundle
  const bootstrapScript = document.createElement("script");
  bootstrapScript.src = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js";
  // bootstrapScript.integrity = "sha384-SOME_OUTDATED_HASH";
  bootstrapScript.crossOrigin = "anonymous";
    document.head.appendChild(bootstrapScript);

  // Append the script to <head> or <body> — either is fine.
    document.head.appendChild(bootstrapScript);

  // 2. (Optional) Your custom JS code can go here
  // Example: Log to console
    console.log("main.js loaded. Dynamically injected Bootstrap 5 JS bundle.");

  // Example: Listen for the script load event
  bootstrapScript.addEventListener("load", () => {
    console.log("Bootstrap 5 JS is now loaded.");
    // You can safely call Bootstrap methods or use its components here if needed.
  });
})();