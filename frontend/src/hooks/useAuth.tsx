import React, { createContext, useContext } from "react";
import { useAuthStore } from "../stores/authStore";
import { oauthService } from "../services/oauth";

interface AuthContextType {
  user: any;
  loading: boolean;
  login: () => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { user, loading, checkAuth } = useAuthStore();

  // Initialize authentication check on mount
  React.useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = () => {
    oauthService.initiateLogin();
  };

  const logout = () => {
    oauthService.logout();
  };

  const isAuthenticated = () => {
    return useAuthStore.getState().isAuthenticated;
  };

  const value: AuthContextType = {
    user,
    loading,
    login,
    logout,
    isAuthenticated,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
