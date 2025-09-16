import { useAuthStore } from "../stores/authStore";

// OAuth2/OpenID Connect configuration
const OAUTH_CONFIG = {
  clientId: "secure-package-manager",
  redirectUri: `${window.location.origin}/oauth/callback`,
  scope: "openid profile email",
  responseType: "code",
  idpBaseUrl: "http://localhost:8081",
};

export class OAuthService {
  private static instance: OAuthService;
  private processingCallback = false;

  static getInstance(): OAuthService {
    if (!OAuthService.instance) {
      OAuthService.instance = new OAuthService();
    }
    return OAuthService.instance;
  }

  // Start OAuth2 authorization flow
  initiateLogin(): void {
    const params = new URLSearchParams({
      client_id: OAUTH_CONFIG.clientId,
      redirect_uri: OAUTH_CONFIG.redirectUri,
      response_type: OAUTH_CONFIG.responseType,
      scope: OAUTH_CONFIG.scope,
      state: this.generateState(),
    });

    const authUrl = `${OAUTH_CONFIG.idpBaseUrl}/oauth/authorize?${params.toString()}`;
    window.location.href = authUrl;
  }

  // Handle OAuth2 callback
  async handleCallback(): Promise<{ success: boolean; error?: string }> {
    const { user, token, isAuthenticated } = useAuthStore.getState();

    // Check if we already have a valid token (avoid re-processing)
    if (isAuthenticated && user && token) {
      console.log("Already authenticated, skipping callback processing...");
      return { success: true };
    }

    // Prevent duplicate processing
    if (this.processingCallback) {
      console.log("OAuth callback already being processed, skipping...");
      return { success: true }; // Return success instead of error for duplicate processing
    }

    console.log("Starting OAuth callback processing...");
    this.processingCallback = true;

    try {
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get("code");
      const state = urlParams.get("state");
      const error = urlParams.get("error");

      console.log(
        "OAuth callback - code:",
        code,
        "state:",
        state,
        "error:",
        error
      );

      if (error) {
        return { success: false, error };
      }

      if (!code) {
        return { success: false, error: "No authorization code received" };
      }

      // Exchange authorization code for tokens
      console.log("Exchanging authorization code for tokens...");
      const tokenResponse = await fetch(
        `${OAUTH_CONFIG.idpBaseUrl}/oauth/token`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: new URLSearchParams({
            grant_type: "authorization_code",
            code: code,
            redirect_uri: OAUTH_CONFIG.redirectUri,
            client_id: OAUTH_CONFIG.clientId,
          }),
        }
      );

      console.log("Token response status:", tokenResponse.status);

      if (!tokenResponse.ok) {
        const errorData = await tokenResponse.json();
        console.error("Token exchange failed:", errorData);
        return {
          success: false,
          error: errorData.error || "Token exchange failed",
        };
      }

      const tokenData = await tokenResponse.json();
      console.log("Token exchange successful");
      const accessToken = tokenData.access_token;
      const idToken = tokenData.id_token;

      // Get user info
      console.log("Getting user info...");
      const userResponse = await fetch(
        `${OAUTH_CONFIG.idpBaseUrl}/oauth/userinfo`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );

      console.log("User info response status:", userResponse.status);

      if (!userResponse.ok) {
        const errorData = await userResponse.json();
        console.error("User info failed:", errorData);
        return { success: false, error: "Failed to get user info" };
      }

      const userData = await userResponse.json();
      console.log("User info retrieved:", userData);

      // Store in localStorage for persistence
      localStorage.setItem("access_token", accessToken);
      localStorage.setItem("id_token", idToken);
      localStorage.setItem("user", JSON.stringify(userData));

      // Store in Zustand store
      useAuthStore.getState().login(userData, accessToken);

      // Clear URL parameters after successful processing
      window.history.replaceState({}, document.title, window.location.pathname);

      return { success: true };
    } catch (error) {
      console.error("OAuth callback error:", error);
      return { success: false, error: "OAuth callback failed" };
    } finally {
      this.processingCallback = false;
    }
  }

  // Get current user
  getCurrentUser(): any {
    return useAuthStore.getState().user;
  }

  // Get access token
  getAccessToken(): string | null {
    return useAuthStore.getState().token;
  }

  // Check if user is authenticated
  isAuthenticated(): boolean {
    return useAuthStore.getState().isAuthenticated;
  }

  // Reset callback processing state (for debugging)
  resetCallbackState(): void {
    console.log("Resetting OAuth callback state...");
    this.processingCallback = false;
  }

  // Logout
  logout(): void {
    useAuthStore.getState().logout();
    this.processingCallback = false; // Reset callback processing state

    // Clear localStorage
    localStorage.removeItem("access_token");
    localStorage.removeItem("id_token");
    localStorage.removeItem("user");
  }

  // Generate random state for CSRF protection
  private generateState(): string {
    return (
      Math.random().toString(36).substring(2, 15) +
      Math.random().toString(36).substring(2, 15)
    );
  }
}

export const oauthService = OAuthService.getInstance();
