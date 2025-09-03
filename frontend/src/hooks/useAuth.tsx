import { useState, useEffect, createContext, useContext } from "react";
import { api, endpoints } from "../services/api";

interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  is_admin: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
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
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in (check localStorage for token)
    const token = localStorage.getItem("token");
    if (token) {
      // Validate token with backend
      api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
      // You could add a token validation endpoint here
      setLoading(false);
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (
    username: string,
    password: string
  ): Promise<boolean> => {
    try {
      const response = await api.post(endpoints.auth.login, {
        username,
        password,
      });
      const { token, user: userData } = response.data;

      localStorage.setItem("token", token);
      api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
      setUser(userData);
      return true;
    } catch (error) {
      console.error("Login failed:", error);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    delete api.defaults.headers.common["Authorization"];
    setUser(null);
  };

  const value: AuthContextType = {
    user,
    loading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
