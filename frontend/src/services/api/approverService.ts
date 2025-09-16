import { useMutation, useQueryClient } from "react-query";
import { api, endpoints } from "../api";
import { BatchApprovalData, BatchRejectionData } from "../../types/approval";

// Batch Approval Mutation
export const useBatchApprove = () => {
  const queryClient = useQueryClient();

  return useMutation(
    async (data: BatchApprovalData) => {
      const response = await api.post(endpoints.approver.batchApprove, data);
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries("packageRequests");
        queryClient.invalidateQueries("approvalRequests");
      },
    }
  );
};

// Batch Rejection Mutation
export const useBatchReject = () => {
  const queryClient = useQueryClient();

  return useMutation(
    async (data: BatchRejectionData) => {
      const response = await api.post(endpoints.approver.batchReject, data);
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries("packageRequests");
        queryClient.invalidateQueries("approvalRequests");
      },
    }
  );
};
