/**
 * MedEdge Intelligence - Global Client Application Script
 * Handles Authentication, Token persistence, Navigation updates, API calls, and Role checking.
 */

const API_BASE = "";

// Helper for API Requests with Auth Token
async function fetchApi(endpoint, options = {}) {
  const token = localStorage.getItem("mededge_token");
  const headers = options.headers || {};

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  options.headers = headers;

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, options);
    if (response.status === 401) {
      // Token expired or invalid
      localStorage.removeItem("mededge_token");
      localStorage.removeItem("mededge_role");
      localStorage.removeItem("mededge_user");
    }
    return response;
  } catch (error) {
    console.error("API Fetch Error:", error);
    throw error;
  }
}

// Update Top Navbar based on session state
async function updateNavbar() {
  const navContainer = document.getElementById("nav-actions");
  if (!navContainer) return;

  const token = localStorage.getItem("mededge_token");
  const role = localStorage.getItem("mededge_role");
  const name = localStorage.getItem("mededge_name");

  if (token && role) {
    let dashboardLink = "/admin";
    if (role === "DOCTOR") dashboardLink = "/doctor";
    else if (role === "NURSE") dashboardLink = "/nurse";
    else if (role === "COMPOUNDER") dashboardLink = "/compounder";
    else if (role === "RECEPTIONIST") dashboardLink = "/reception";
    else if (role === "PATIENT") dashboardLink = "/patient/dashboard";

    navContainer.innerHTML = `
      <span class="user-badge">
        <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>
        ${name || 'User'} (${role})
      </span>
      <li class="nav-item"><a href="${dashboardLink}" class="btn-nav-primary">My Dashboard</a></li>
      <li class="nav-item"><a href="/telemetry">Live Telemetry</a></li>
      <li class="nav-item"><a href="#" onclick="logoutUser(event)">Logout</a></li>
    `;
  } else {
    navContainer.innerHTML = `
      <li class="nav-item"><a href="/">Home</a></li>
      <li class="nav-item"><a href="/telemetry">Live Telemetry</a></li>
      <li class="nav-item"><a href="/patient-login">Patient Login</a></li>
      <li class="nav-item"><a href="/login" class="btn-nav-primary">Staff Login</a></li>
    `;
  }
}

// User Logout Function
function logoutUser(e) {
  if (e) e.preventDefault();
  localStorage.removeItem("mededge_token");
  localStorage.removeItem("mededge_role");
  localStorage.removeItem("mededge_name");
  window.location.href = "/login";
}

// Auto-run on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  updateNavbar();
});
