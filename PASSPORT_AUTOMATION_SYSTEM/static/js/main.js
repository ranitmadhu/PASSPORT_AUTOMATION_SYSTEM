/**
 * Passport Automation System (PAS) JavaScript Handlers
 */

document.addEventListener("DOMContentLoaded", function () {
  // Public Live Tracker Handler
  const trackBtn = document.getElementById("track-btn");
  const appNumberInput = document.getElementById("track-app-num");
  const trackResultContainer = document.getElementById("track-result-container");

  if (trackBtn && appNumberInput) {
    trackBtn.addEventListener("click", function () {
      const appNum = appNumberInput.value.trim();
      if (!appNum) {
        alert("Please enter a valid Application Number (e.g., PAS-2026-XXXXXX).");
        return;
      }

      trackBtn.disabled = true;
      trackBtn.innerText = "Searching...";

      fetch(`/api/track/${encodeURIComponent(appNum)}`)
        .then((response) => response.json())
        .then((data) => {
          trackBtn.disabled = false;
          trackBtn.innerText = "Track Status";
          trackResultContainer.style.display = "block";

          if (data.found) {
            let statusBadgeClass = `badge-${data.status}`;
            trackResultContainer.innerHTML = `
              <div class="card" style="border-left: 5px solid var(--primary-light);">
                <div class="card-body">
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4>Application #${data.application_number}</h4>
                    <span class="badge ${statusBadgeClass}">${data.status.replace(/_/g, ' ').toUpperCase()}</span>
                  </div>
                  <p style="margin-top: 0.5rem;"><strong>Applicant Name:</strong> ${data.applicant_name}</p>
                  <p><strong>Application Type:</strong> ${data.application_type.toUpperCase()}</p>
                  <p><strong>Submission Date:</strong> ${data.created_at}</p>
                  ${data.passport_number !== 'N/A' ? `<p style="color: var(--success-text); font-weight: 700;">Passport Number: ${data.passport_number}</p>` : ''}
                  ${data.dispatch_tracking_id !== 'N/A' ? `<p style="color: var(--info-text); font-weight: 700;">Speed Post Tracking: ${data.dispatch_tracking_id}</p>` : ''}
                </div>
              </div>
            `;
          } else {
            trackResultContainer.innerHTML = `
              <div class="alert alert-danger">
                No application record found for Number: <strong>${appNum}</strong>. Please verify the application number and try again.
              </div>
            `;
          }
        })
        .catch((err) => {
          trackBtn.disabled = false;
          trackBtn.innerText = "Track Status";
          alert("Error connecting to server. Please try again.");
          console.error(err);
        });
    });
  }

  // Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach((alert) => {
    setTimeout(() => {
      alert.style.opacity = "0";
      alert.style.transition = "opacity 0.5s ease-out";
      setTimeout(() => alert.remove(), 500);
    }, 5000);
  });
});

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = "flex";
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = "none";
  }
}
