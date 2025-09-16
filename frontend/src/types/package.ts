// Package and Package Request Types
import { PackageStatus } from "./packageStatus";

export interface ScanResult {
  scan_duration_ms: number | null;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  scan_type: string;
  trivy_version: string | null;
  created_at: string | null;
  completed_at: string | null;
}

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
  scan_result: ScanResult | null;
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
