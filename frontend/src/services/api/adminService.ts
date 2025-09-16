import { useQuery, useMutation, useQueryClient } from "react-query";
import { api, endpoints } from "../api";
import { ConfigStatus, ConfigData } from "../../types/config";

// Configuration Queries
export const useConfigStatus = () => {
  return useQuery<ConfigStatus>("configStatus", async () => {
    const response = await api.get(endpoints.admin.config);
    return response.data.status;
  });
};

export const useConfigData = () => {
  return useQuery<ConfigData>("configData", async () => {
    const response = await api.get(endpoints.admin.config);
    return response.data.config;
  });
};

// Configuration Mutations
export const useUpdateConfig = () => {
  const queryClient = useQueryClient();

  return useMutation(
    async (configData: Partial<ConfigData>) => {
      const response = await api.put(endpoints.admin.config, configData);
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries("configStatus");
        queryClient.invalidateQueries("configData");
      },
    }
  );
};

// Validated Packages Query
export const useValidatedPackages = () => {
  return useQuery("validatedPackages", async () => {
    const response = await api.get(endpoints.admin.validatedPackages);
    return response.data;
  });
};

// Publish Package Mutation
export const usePublishPackage = () => {
  const queryClient = useQueryClient();

  return useMutation(
    async (packageId: number) => {
      const response = await api.post(
        endpoints.admin.publishPackage(packageId)
      );
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries("packageRequests");
        queryClient.invalidateQueries("validatedPackages");
      },
    }
  );
};
