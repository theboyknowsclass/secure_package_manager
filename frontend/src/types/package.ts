// Package and Package Request Types
import { PackageStatus } from "./packageStatus";

export interface Package {
  id: number;
  name: string;
  version: string;
  status: PackageStatus;
  security_score: number | null;
  license_score: number | null;
  license_status: string | null;
  security_scan_status: string;
  license_identifier: string | null;
  approver_id: number | null;
  rejector_id: number | null;
  published_at: string | null;
  type?: "new" | "existing";
  vulnerability_count?: number;
  critical_vulnerabilities?: number;
}

export interface PackageRequest {
  id: number;
  application_name: string;
  version: string;
  status: PackageStatus;
  requestor: {
    id: number;
    username: string;
    full_name: string;
  };
  created_at: string;
  updated_at: string;
  total_packages: number;
  completion_percentage: number;
  packages: Package[];
  package_counts: {
    total: number;
    Requested: number;
    "Checking Licence": number;
    "Licence Checked": number;
    Downloading: number;
    Downloaded: number;
    "Security Scanning": number;
    "Security Scanned": number;
    "Pending Approval": number;
    Approved: number;
    Rejected: number;
  };
}

export interface DetailedRequestResponse {
  request: PackageRequest;
  packages: Package[];
}
