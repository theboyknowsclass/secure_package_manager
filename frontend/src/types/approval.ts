// Approval Types

export interface BatchApprovalData {
  package_ids: number[];
  request_id: number;
}

export interface BatchRejectionData {
  package_ids: number[];
  request_id: number;
  reason?: string;
}
