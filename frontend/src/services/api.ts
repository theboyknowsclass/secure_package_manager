import axios from "axios";
import { handleUnauthorized } from "../utils/auth";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add request interceptor to include auth token
api.interceptors.request.use(
  config => {
    // Try OAuth2 token first, then fallback to legacy token
    const token =
      localStorage.getItem("access_token") || localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle auth errors
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Token expired or invalid - clear all auth storage and redirect
      handleUnauthorized();
    }
    return Promise.reject(error);
  }
);

// API endpoints
export const endpoints = {
  auth: {
    login: "/api/auth/login",
  },
  packages: {
    upload: "/api/packages/upload",
    requests: "/api/packages/requests",
    request: (id: number) => `/api/packages/requests/${id}`,
  },
  admin: {
    validatedPackages: "/api/admin/packages/validated",
    publishPackage: (id: number) => `/api/approver/packages/publish/${id}`,
    licenses: (status?: string) =>
      status ? `/api/admin/licenses?status=${status}` : "/api/admin/licenses",
    license: (id: number) => `/api/admin/licenses/${id}`,
    config: "/api/admin/config",
  },
  approver: {
    batchApprove: "/api/approver/packages/batch-approve",
    batchReject: "/api/approver/packages/batch-reject",
  },
};
