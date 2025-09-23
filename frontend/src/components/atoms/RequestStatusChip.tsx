import React from "react";
import { Tooltip, Chip } from "@mui/material";

export interface RequestStatusChipProps {
  status: string;
  showTooltip?: boolean;
  size?: "small" | "medium";
  variant?: "filled" | "outlined";
}

const getRequestStatusColor = (status: string) => {
  switch (status) {
    case "pending_approval":
      return "warning";
    case "approved":
      return "success";
    case "rejected":
      return "error";
    case "processing":
      return "info";
    default:
      return "default";
  }
};

const getRequestStatusLabel = (status: string): string => {
  switch (status) {
    case "pending_approval":
      return "Pending Approval";
    case "approved":
      return "Approved";
    case "rejected":
      return "Rejected";
    case "processing":
      return "Processing";
    default:
      return status;
  }
};

export const RequestStatusChip: React.FC<RequestStatusChipProps> = React.memo(
  ({ status, showTooltip = true, size = "small", variant = "filled" }) => {
    const color = getRequestStatusColor(status);
    const label = getRequestStatusLabel(status);

    const chip = (
      <Chip label={label} color={color} size={size} variant={variant} />
    );

    if (showTooltip) {
      return <Tooltip title={`Request Status: ${label}`}>{chip}</Tooltip>;
    }

    return chip;
  }
);

export default RequestStatusChip;
