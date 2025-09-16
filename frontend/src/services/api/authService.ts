import { useQuery, useMutation } from "react-query";
import { api, endpoints } from "../api";
import { LoginCredentials, AuthUser, AuthResponse } from "../../types/auth";

// Auth Queries
export const useCurrentUser = () => {
  return useQuery<AuthUser>(
    "currentUser",
    async () => {
      const response = await api.get("/api/auth/me");
      return response.data.user;
    },
    {
      retry: false,
      refetchOnWindowFocus: false,
    }
  );
};

// Auth Mutations
export const useLogin = () => {
  return useMutation<AuthResponse, Error, LoginCredentials>(
    async (credentials: LoginCredentials) => {
      const response = await api.post(endpoints.auth.login, credentials);
      return response.data;
    }
  );
};

export const useLogout = () => {
  return useMutation(async () => {
    const response = await api.post("/api/auth/logout");
    return response.data;
  });
};
