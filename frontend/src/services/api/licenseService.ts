import { useQuery, useMutation, useQueryClient } from "react-query";
import { api, endpoints } from "../api";
import {
  SupportedLicense,
  CreateLicenseData,
  UpdateLicenseData,
} from "../../types/license";

// License Queries
export const useLicenses = (status?: string) => {
  return useQuery<SupportedLicense[]>(
    ["supportedLicenses", status],
    async () => {
      const response = await api.get(endpoints.admin.licenses(status));
      return response.data.licenses;
    }
  );
};

// License Mutations
export const useCreateLicense = () => {
  const queryClient = useQueryClient();

  return useMutation(
    async (licenseData: CreateLicenseData) => {
      const response = await api.post(endpoints.admin.licenses(), licenseData);
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(["supportedLicenses"]);
      },
    }
  );
};

export const useUpdateLicense = () => {
  const queryClient = useQueryClient();

  return useMutation(
    async ({ id, data }: { id: number; data: UpdateLicenseData }) => {
      const response = await api.put(endpoints.admin.license(id), data);
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(["supportedLicenses"]);
      },
    }
  );
};

export const useDeleteLicense = () => {
  const queryClient = useQueryClient();

  return useMutation(
    async (id: number) => {
      const response = await api.delete(endpoints.admin.license(id));
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(["supportedLicenses"]);
      },
    }
  );
};
