// Authentication and User Types

export interface AuthUser {
  id: number;
  username: string;
  full_name: string;
  role: "admin" | "approver" | "user";
  email?: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthResponse {
  user: AuthUser;
  token: string;
  access_token?: string;
}
