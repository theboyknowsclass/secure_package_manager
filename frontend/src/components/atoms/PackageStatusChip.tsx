import React from "react";
import { Tooltip } from "@mui/material";
import { StatusChip } from "./StatusChip";
import { PACKAGE_STATUS, type PackageStatus } from "../../types/packageStatus";

export interface PackageStatusChipProps {
  status: PackageStatus;
  showTooltip?: boolean;
  size?: "small" | "medium";
  variant?: "filled" | "outlined";
}

const getPackageStatusColor = (status: PackageStatus) => {
  switch (status) {
    case PACKAGE_STATUS.APPROVED:
      return "success";
    case PACKAGE_STATUS.REJECTED:
      return "error";
    case PACKAGE_STATUS.PENDING_APPROVAL:
      return "info";
    default:
      return "warning";
  }
};

const getPackageStatusLabel = (status: PackageStatus): string => {
  switch (status) {
    case PACKAGE_STATUS.REQUESTED:
      return "Requested";
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
    default:
      return status;
  }
};

export const PackageStatusChip: React.FC<PackageStatusChipProps> = ({
  status,
  showTooltip = true,
  size = "small",
  variant = "filled",
}) => {
  const color = getPackageStatusColor(status);
  const label = getPackageStatusLabel(status);

  const chip = (
    <StatusChip status={label} color={color} size={size} variant={variant} />
  );

  if (showTooltip) {
    return <Tooltip title={`Status: ${label}`}>{chip}</Tooltip>;
  }

  return chip;
};

export default PackageStatusChip;
