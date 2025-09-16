// License Types

export interface SupportedLicense {
  id: number;
  name: string;
  identifier: string;
  status: "always_allowed" | "allowed" | "avoid" | "blocked";
  created_by: number;
  created_at: string;
  updated_at: string;
}

export interface CreateLicenseData {
  name: string;
  identifier: string;
  status: "always_allowed" | "allowed" | "avoid" | "blocked";
}

export interface UpdateLicenseData {
  name: string;
  status: "always_allowed" | "allowed" | "avoid" | "blocked";
}
