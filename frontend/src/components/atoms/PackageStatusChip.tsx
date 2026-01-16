import React from "react";
import { Tooltip, Chip } from "@mui/material";
import { PACKAGE_STATUS, type PackageStatus } from "../../types/packageStatus";

export interface PackageStatusChipProps {
  status: PackageStatus | string;
  showTooltip?: boolean;
  size?: "small" | "medium";
  variant?: "filled" | "outlined";
}

const getPackageStatusColor = (status: PackageStatus | string) => {
  // status column on the status page
  console.log("getPackageStatusColor: status =", status);
  switch (status) {
    case PACKAGE_STATUS.APPROVED:
      return "success";
    case PACKAGE_STATUS.REJECTED:
      return "error";
    case PACKAGE_STATUS.PENDING_APPROVAL:
      return "info";
    case PACKAGE_STATUS.PROCESSING:
      return "info";
    // Handle request status strings returned by backend
    case "pending_approval":
      return "info";
    case "processing":
      return "info";
    case "approved":
      return "success";
    case "rejected":
      return "error";
    default:
      return "warning";
  }
};

const getPackageStatusLabel = (status: PackageStatus | string): string => {
  // status inside the panel for the status column
  console.log("getPackageStatusLabel: status =", status);
  switch (status) {
    case PACKAGE_STATUS.SUBMITTED:
      return "Submitted";
    case PACKAGE_STATUS.PARSED:
      return "Parsed";
    case PACKAGE_STATUS.CHECKING_LICENCE:
      return "Checking License";
    case PACKAGE_STATUS.LICENCE_CHECKED:
      return "License Checked";
    case PACKAGE_STATUS.DOWNLOADING:
      return "Downloading";
    case PACKAGE_STATUS.DOWNLOADED:
      return "Downloaded";
    case PACKAGE_STATUS.SECURITY_SCANNING:
      return "Security Scanning";
    case PACKAGE_STATUS.SECURITY_SCANNED:
      return "Security Scanned";
    case PACKAGE_STATUS.PENDING_APPROVAL:
      return "Pending Approval";
    case PACKAGE_STATUS.APPROVED:
      return "Approved";
    case PACKAGE_STATUS.REJECTED:
      return "Rejected";
    case PACKAGE_STATUS.PROCESSING:
      return "Processing";
    default:
      return status;
  }
};

export const PackageStatusChip: React.FC<PackageStatusChipProps> = React.memo(
  ({ status, showTooltip = true, size = "small", variant = "filled" }) => {
    const color = getPackageStatusColor(status);
    const label = getPackageStatusLabel(status);

    const chip = (
      <Chip label={label} color={color} size={size} variant={variant} />
    );
    
    // hovering over the status label on the status page
    if (showTooltip) {
      return <Tooltip title={`Status: ${label}`}>{chip}</Tooltip>;
    }

    return chip;
  }
);

export default PackageStatusChip;
