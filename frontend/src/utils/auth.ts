/**
 * Authentication utility functions
 */

/**
 * Clear all authentication-related storage from both localStorage and sessionStorage
 */
export const clearAuthStorage = (): void => {
  console.log("Clearing all authentication storage...");

  // Clear localStorage
  localStorage.removeItem("access_token");
  localStorage.removeItem("id_token");
  localStorage.removeItem("user");
  localStorage.removeItem("token");
  localStorage.removeItem("auth_state");
  localStorage.removeItem("auth_nonce");

  // Clear sessionStorage
  sessionStorage.removeItem("access_token");
  sessionStorage.removeItem("id_token");
  sessionStorage.removeItem("user");
  sessionStorage.removeItem("token");
  sessionStorage.removeItem("auth_state");
  sessionStorage.removeItem("auth_nonce");

  console.log("Authentication storage cleared");
};

/**
 * Handle 401 Unauthorized response by clearing storage and redirecting
 */
export const handleUnauthorized = (): void => {
  console.warn(
    "401 Unauthorized - clearing authentication storage and redirecting to login"
  );
  clearAuthStorage();
  window.location.href = "/login";
};
