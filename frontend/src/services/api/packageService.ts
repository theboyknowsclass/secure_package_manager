import { useQuery, useMutation, useQueryClient } from "react-query";
import { api, endpoints } from "../api";
import {
  PackageRequest,
  DetailedRequestResponse,
  AuditDataItem,
} from "../../types/package";

// Package Request Queries
export const usePackageRequests = (options?: { refetchInterval?: number }) => {
  return useQuery<PackageRequest[]>(
    "packageRequests",
    async () => {
      const response = await api.get(endpoints.packages.requests);
      return response.data.requests;
    },
    {
      refetchInterval: options?.refetchInterval || 5000,
      refetchIntervalInBackground: true,
    }
  );
};

export const usePackageRequest = (
  requestId: number,
  options?: { refetchInterval?: number }
) => {
  return useQuery<DetailedRequestResponse>(
    ["packageRequest", requestId],
    async () => {
      const response = await api.get(endpoints.packages.request(requestId));
      return response.data;
    },
    {
      enabled: !!requestId,
      refetchInterval: options?.refetchInterval || 5000,
      refetchIntervalInBackground: true,
    }
  );
};

// Package Upload Mutation
export const usePackageUpload = () => {
  const queryClient = useQueryClient();

  return useMutation(
    async (formData: FormData) => {
      const response = await api.post(endpoints.packages.upload, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      return response.data;
    },
    {
      onSuccess: () => {
        // Invalidate and refetch package requests
        queryClient.invalidateQueries("packageRequests");
      },
    }
  );
};

// Approval Dashboard specific query
export const useApprovalRequests = () => {
  return useQuery<PackageRequest[]>("approvalRequests", async () => {
    const response = await api.get(endpoints.packages.requests);
    return response.data.requests;
  });
};

// Audit data query
export const useAuditData = () => {
  return useQuery<AuditDataItem[]>(
    "auditData",
    async () => {
      try {
        const response = await api.get(endpoints.packages.audit);
        console.log("Fetched audit data:", response.data.audit_data);
        console.log("Response status:", response.status);
        return response.data.audit_data;
      } catch (error) {
        console.error("Error fetching audit data:", error);
        throw error;
      }
    },
    {
      refetchInterval: 30000, // Refetch every 30 seconds
      refetchIntervalInBackground: true,
      staleTime: 10000, // Consider data fresh for 10 seconds
      cacheTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
      retry: (failureCount, error) => {
        console.log(`Audit data fetch failed (attempt ${failureCount + 1}):`, error);
        return failureCount < 3; // Retry up to 3 times
      },
      onError: (error) => {
        console.error("Final error fetching audit data:", error);
      },
    }
  );
};
