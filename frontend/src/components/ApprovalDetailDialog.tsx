import React, { useState } from "react";
import {
  Box,
  Typography,
  CircularProgress,
  Chip,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Grid,
  Card,
  CardContent,
  Tooltip,
} from "@mui/material";
import { MaterialReactTable, type MRT_ColumnDef } from "material-react-table";
import { 
  Close, 
  CheckCircle, 
  Cancel 
} from "@mui/icons-material";
import { api, endpoints } from "../services/api";
import { 
  PACKAGE_STATUS, 
  LICENSE_STATUS,
  type PackageStatus,
  type LicenseStatus,
  type Package,
  type DetailedRequestResponse
} from "../types/status";

interface ApprovalDetailDialogProps {
  open: boolean;
  onClose: () => void;
  selectedRequest: DetailedRequestResponse | null;
  onApprovalComplete: () => void;
}

// Define columns for package details table with selection
const packageColumns: MRT_ColumnDef<Package & { selected?: boolean; onSelectChange?: (selected: boolean) => void }>[] = [
  {
    accessorKey: "select",
    header: "Select",
    size: 60,
    Cell: ({ row }) => {
      const isPendingApproval = row.original.status === PACKAGE_STATUS.PENDING_APPROVAL;
      return (
        <input
          type="checkbox"
          checked={row.original.selected || false}
          disabled={!isPendingApproval}
          onChange={(e) => {
            if (row.original.onSelectChange && isPendingApproval) {
              row.original.onSelectChange(e.target.checked);
            }
          }}
          style={{
            opacity: isPendingApproval ? 1 : 0.5,
            cursor: isPendingApproval ? 'pointer' : 'not-allowed'
          }}
        />
      );
    },
  },
  {
    accessorKey: "name",
    header: "Package",
    size: 200,
    Cell: ({ row }) => (
      <Typography variant="body2" sx={{ fontWeight: "medium" }}>
        {row.original.name}
      </Typography>
    ),
  },
  {
    accessorKey: "version",
    header: "Version",
    size: 120,
    Cell: ({ row }) => (
      <Typography variant="body2">
        {row.original.version}
      </Typography>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    size: 120,
    Cell: ({ row }) => (
      <Chip
        label={getPackageStatusLabel(row.original.status)}
        color={getPackageStatusColor(row.original.status)}
        size="small"
      />
    ),
  },
  {
    accessorKey: "license_identifier",
    header: "License",
    size: 150,
    Cell: ({ row }) => {
      const pkg = row.original;
      if (!pkg.license_identifier) {
        return <Typography variant="body2" color="textSecondary">Unknown</Typography>;
      }
      
      // Parse license expression to separate individual licenses
      const parseLicenseExpression = (expression: string): string[] => {
        return expression
          .replace(/[()]/g, '')
          .split(/\s+(?:OR|AND)\s+/i)
          .map(license => license.trim())
          .filter(license => license.length > 0);
      };
      
      const licenses = parseLicenseExpression(pkg.license_identifier);
      
      if (licenses.length === 1) {
        return (
          <Chip
            label={licenses[0]}
            color={getLicenseStatusColor(licenses[0])}
            size="small"
          />
        );
      }
      
      return (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
          {licenses.map((license, index) => (
            <Chip
              key={index}
              label={license}
              color={getLicenseStatusColor(license)}
              size="small"
            />
          ))}
        </Box>
      );
    },
  },
  {
    accessorKey: "security_score",
    header: "Security",
    size: 100,
    Cell: ({ row }) => {
      const score = row.original.security_score;
      if (score === null) {
        return <Typography variant="body2" color="textSecondary">-</Typography>;
      }
      return (
        <Chip
          label={`${score}/100`}
          color={score >= 80 ? "success" : score >= 60 ? "warning" : "error"}
          size="small"
        />
      );
    },
  },
  {
    accessorKey: "vulnerabilities",
    header: "Vulnerabilities",
    size: 120,
    Cell: ({ row }) => {
      const pkg = row.original;
      const total = pkg.vulnerability_count || 0;
      const critical = pkg.critical_vulnerabilities || 0;
      
      if (total === 0) {
        return <Typography variant="body2" color="success.main">None</Typography>;
      }
      
      return (
        <Box>
          <Typography variant="body2" color={critical > 0 ? "error.main" : "warning.main"}>
            {total} total
          </Typography>
          {critical > 0 && (
            <Typography variant="caption" color="error.main">
              {critical} critical
            </Typography>
          )}
        </Box>
      );
    },
  },
  {
    accessorKey: "type",
    header: "Type",
    size: 80,
    Cell: ({ row }) => (
      <Chip
        label={row.original.type === "existing" ? "Existing" : "New"}
        color={row.original.type === "existing" ? "success" : "primary"}
        size="small"
      />
    ),
  },
];

export default function ApprovalDetailDialog({
  open,
  onClose,
  selectedRequest,
  onApprovalComplete,
}: ApprovalDetailDialogProps) {
  const [approvalReason, setApprovalReason] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedPackages, setSelectedPackages] = useState<Set<number>>(new Set());

  const handlePackageSelect = (packageId: number, selected: boolean) => {
    setSelectedPackages(prev => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(packageId);
      } else {
        newSet.delete(packageId);
      }
      return newSet;
    });
  };

  const handleSelectAll = (selected: boolean) => {
    if (!selectedRequest) return;
    const pendingPackageIds = selectedRequest.packages
      .filter(pkg => pkg.status === PACKAGE_STATUS.PENDING_APPROVAL)
      .map(pkg => pkg.id);
    
    if (selected) {
      setSelectedPackages(new Set(pendingPackageIds));
    } else {
      setSelectedPackages(new Set());
    }
  };

  const handleApproveRequest = async () => {
    if (!selectedRequest || selectedPackages.size === 0) return;
    
    // Double-check that all selected packages are actually pending approval
    const selectedPendingPackages = Array.from(selectedPackages).filter(packageId => {
      const pkg = selectedRequest.packages.find(p => p.id === packageId);
      return pkg && pkg.status === PACKAGE_STATUS.PENDING_APPROVAL;
    });
    
    if (selectedPendingPackages.length === 0) {
      console.warn("No pending approval packages selected for approval");
      return;
    }
    
    setIsProcessing(true);
    try {
      const response = await api.post(endpoints.approver.batchApprove, {
        package_ids: selectedPendingPackages,
        reason: approvalReason || "Approved by administrator"
      });
      
      console.log("Batch approval response:", response.data);
      onApprovalComplete();
      handleClose();
      
    } catch (error) {
      console.error("Error approving packages:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRejectRequest = async () => {
    if (!selectedRequest || selectedPackages.size === 0) return;
    
    // Double-check that all selected packages are actually pending approval
    const selectedPendingPackages = Array.from(selectedPackages).filter(packageId => {
      const pkg = selectedRequest.packages.find(p => p.id === packageId);
      return pkg && pkg.status === PACKAGE_STATUS.PENDING_APPROVAL;
    });
    
    if (selectedPendingPackages.length === 0) {
      console.warn("No pending approval packages selected for rejection");
      return;
    }
    
    setIsProcessing(true);
    try {
      const response = await api.post(endpoints.approver.batchReject, {
        package_ids: selectedPendingPackages,
        reason: rejectionReason || "Rejected by administrator"
      });
      
      console.log("Batch rejection response:", response.data);
      onApprovalComplete();
      handleClose();
      
    } catch (error) {
      console.error("Error rejecting packages:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleClose = () => {
    setApprovalReason("");
    setRejectionReason("");
    setSelectedPackages(new Set());
    onClose();
  };

  // Helper function to get only pending approval packages from selected packages
  const getSelectedPendingPackages = () => {
    if (!selectedRequest) return [];
    return Array.from(selectedPackages).filter(packageId => {
      const pkg = selectedRequest.packages.find(p => p.id === packageId);
      return pkg && pkg.status === PACKAGE_STATUS.PENDING_APPROVAL;
    });
  };

  // Helper function to check if any pending approval packages are selected
  const hasSelectedPendingPackages = () => {
    return getSelectedPendingPackages().length > 0;
  };

  const getLicenseSummary = (packages: Package[]) => {
    const licenseCounts: { [key: string]: number } = {};
    const licenseCategories: { [key: string]: string } = {};
    
    const categorizeLicense = (licenseExpression: string): string => {
      const hasAllowed = licenseExpression.includes("MIT") || 
                        licenseExpression.includes("Apache-2.0") || 
                        licenseExpression.includes("BSD") ||
                        licenseExpression.includes("CC0-1.0") ||
                        licenseExpression.includes("Unlicense") ||
                        licenseExpression.includes("ISC") ||
                        licenseExpression.includes("0BSD");
      
      const hasBlocked = licenseExpression.includes("GPL-3.0") || 
                        licenseExpression.includes("LGPL-3.0") ||
                        licenseExpression.includes("AGPL");
      
      const hasAvoid = licenseExpression.includes("GPL-2.0") || 
                      licenseExpression.includes("LGPL-2.0");
      
      if (licenseExpression.includes(" OR ") && hasAllowed && !hasBlocked) {
        return "Allowed";
      }
      
      if (licenseExpression.includes(" AND ")) {
        if (hasBlocked) return "Blocked";
        if (hasAvoid) return "Avoid";
        return "Review";
      }
      
      if (["MIT", "Apache-2.0", "BSD", "CC0-1.0", "Unlicense", "ISC", "0BSD"].some(l => licenseExpression.includes(l))) {
        return "Allowed";
      } else if (["GPL-3.0", "LGPL-3.0", "AGPL"].some(l => licenseExpression.includes(l))) {
        return "Blocked";
      } else if (["GPL-2.0", "LGPL-2.0"].some(l => licenseExpression.includes(l))) {
        return "Avoid";
      } else {
        return "Review";
      }
    };
    
    packages.forEach(pkg => {
      const license = pkg.license_identifier || "Unknown";
      licenseCounts[license] = (licenseCounts[license] || 0) + 1;
      licenseCategories[license] = categorizeLicense(license);
    });
    
    return { licenseCounts, licenseCategories };
  };

  return (
    <Dialog 
      open={open} 
      onClose={handleClose}
      maxWidth="lg"
      fullWidth
      sx={{ zIndex: 9999 }}
    >
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">
            Package Approval {selectedRequest ? `- ID #${selectedRequest.request.id}` : '- Loading...'}
          </Typography>
          <IconButton onClick={handleClose} size="small">
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        {selectedRequest ? (
          <Box>
            {/* Request Summary */}
            <Box sx={{ mb: 3, p: 2, bgcolor: "grey.50", borderRadius: 1 }}>
              <Typography variant="h6" gutterBottom>
                Request Summary
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={4}>
                  <Typography variant="caption" color="textSecondary">
                    Application
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                    {selectedRequest.request.application_name} v{selectedRequest.request.version}
                  </Typography>
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="caption" color="textSecondary">
                    Requestor
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                    {selectedRequest.request.requestor.full_name} (@{selectedRequest.request.requestor.username})
                  </Typography>
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="caption" color="textSecondary">
                    Created
                  </Typography>
                  <Typography variant="body2">
                    {new Date(selectedRequest.request.created_at).toLocaleString()}
                  </Typography>
                </Grid>
              </Grid>
            </Box>

            {/* License Summary */}
            <Box sx={{ mb: 3, p: 2, bgcolor: "blue.50", borderRadius: 1 }}>
              <Typography variant="h6" gutterBottom>
                License Summary
              </Typography>
              {(() => {
                const { licenseCounts, licenseCategories } = getLicenseSummary(selectedRequest.packages);
                
                const individualLicenseCounts: { [key: string]: number } = {};
                
                Object.entries(licenseCounts).forEach(([licenseExpression, count]) => {
                  const individualLicenses = licenseExpression
                    .replace(/[()]/g, '')
                    .split(/\s+(?:OR|AND)\s+/i)
                    .map(license => license.trim())
                    .filter(license => license.length > 0);
                  
                  individualLicenses.forEach(license => {
                    individualLicenseCounts[license] = (individualLicenseCounts[license] || 0) + count;
                  });
                });
                
                return (
                  <Grid container spacing={2}>
                    {Object.entries(individualLicenseCounts).map(([license, count]) => (
                      <Grid item xs={3} key={license}>
                        <Box sx={{ textAlign: "center" }}>
                          <Chip
                            label={`${count} ${license}`}
                            color={getLicenseStatusColor(license)}
                            size="small"
                          />
                          <Typography variant="caption" color="textSecondary" sx={{ display: "block", mt: 0.5 }}>
                            {getLicenseCategory(license)}
                          </Typography>
                        </Box>
                      </Grid>
                    ))}
                  </Grid>
                );
              })()}
            </Box>

            {/* Approval Actions */}
            <Box sx={{ mb: 3 }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                <Typography variant="h6">
                  Approval Actions
                </Typography>
                <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                  <Typography variant="body2" color="textSecondary">
                    {getSelectedPendingPackages().length} of {selectedRequest.packages.filter(p => p.status === PACKAGE_STATUS.PENDING_APPROVAL).length} pending packages selected
                  </Typography>
                  <Button
                    size="small"
                    onClick={() => handleSelectAll(true)}
                    disabled={selectedPackages.size === selectedRequest.packages.filter(p => p.status === PACKAGE_STATUS.PENDING_APPROVAL).length}
                  >
                    Select All Pending
                  </Button>
                  <Button
                    size="small"
                    onClick={() => handleSelectAll(false)}
                    disabled={selectedPackages.size === 0}
                  >
                    Clear All
                  </Button>
                </Box>
              </Box>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Card sx={{ border: "1px solid", borderColor: "success.main" }}>
                    <CardContent>
                      <Box display="flex" alignItems="center" mb={2}>
                        <CheckCircle color="success" sx={{ mr: 1 }} />
                        <Typography variant="h6" color="success.main">
                          Approve Request
                        </Typography>
                      </Box>
                      <TextField
                        fullWidth
                        multiline
                        rows={3}
                        placeholder="Optional approval reason..."
                        value={approvalReason}
                        onChange={(e) => setApprovalReason(e.target.value)}
                        size="small"
                      />
                      <Button
                        fullWidth
                        variant="contained"
                        color="success"
                        startIcon={<CheckCircle />}
                        onClick={handleApproveRequest}
                        disabled={isProcessing || !hasSelectedPendingPackages()}
                        sx={{ mt: 2 }}
                      >
                        Approve Selected ({getSelectedPendingPackages().length})
                      </Button>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card sx={{ border: "1px solid", borderColor: "error.main" }}>
                    <CardContent>
                      <Box display="flex" alignItems="center" mb={2}>
                        <Cancel color="error" sx={{ mr: 1 }} />
                        <Typography variant="h6" color="error.main">
                          Reject Request
                        </Typography>
                      </Box>
                      <TextField
                        fullWidth
                        multiline
                        rows={3}
                        placeholder="Rejection reason (required)..."
                        value={rejectionReason}
                        onChange={(e) => setRejectionReason(e.target.value)}
                        size="small"
                        required
                      />
                      <Button
                        fullWidth
                        variant="contained"
                        color="error"
                        startIcon={<Cancel />}
                        onClick={handleRejectRequest}
                        disabled={isProcessing || !rejectionReason.trim() || !hasSelectedPendingPackages()}
                        sx={{ mt: 2 }}
                      >
                        Reject Selected ({getSelectedPendingPackages().length})
                      </Button>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </Box>

            {/* Packages Table */}
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
              <Typography variant="h6">
                Packages ({selectedRequest.packages.length})
              </Typography>
              <Typography variant="caption" color="textSecondary">
                Only packages with "Pending Approval" status can be selected for approval/rejection
              </Typography>
            </Box>
            
            <MaterialReactTable
              columns={packageColumns}
              data={selectedRequest.packages.map(pkg => ({
                ...pkg,
                selected: selectedPackages.has(pkg.id),
                onSelectChange: (selected: boolean) => handlePackageSelect(pkg.id, selected)
              }))}
              enableColumnFilters
              enableGlobalFilter
              enableSorting
              enableColumnResizing
              enablePagination={false}
              enableTopToolbar={false}
              enableBottomToolbar={false}
              enableColumnFilterModes={false}
              muiTableProps={{
                sx: {
                  tableLayout: "fixed",
                },
              }}
              muiTableContainerProps={{
                sx: {
                  maxHeight: "400px",
                },
              }}
              muiTableHeadProps={{
                sx: {
                  position: "sticky",
                  top: 0,
                  zIndex: 1,
                  backgroundColor: "background.paper",
                },
              }}
              muiTableBodyRowProps={({ row }) => ({
                sx: {
                  opacity: row.original.status === PACKAGE_STATUS.PENDING_APPROVAL ? 1 : 0.6,
                  backgroundColor: row.original.status === PACKAGE_STATUS.PENDING_APPROVAL 
                    ? "transparent" 
                    : "rgba(0, 0, 0, 0.02)",
                },
              })}
              initialState={{
                density: "compact",
                showColumnFilters: true,
                sorting: [
                  { id: "name", desc: false },
                  { id: "version", desc: false },
                ],
              }}
            />
          </Box>
        ) : (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
            <CircularProgress />
            <Typography variant="body2" sx={{ ml: 2 }}>
              Loading package details...
            </Typography>
          </Box>
        )}
      </DialogContent>
      
      <DialogActions>
        <Button onClick={handleClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}

// Helper functions
function getPackageStatusColor(status: string) {
  switch (status) {
    case PACKAGE_STATUS.APPROVED:
      return "success"; // Green
    case PACKAGE_STATUS.REJECTED:
      return "error"; // Red
    case PACKAGE_STATUS.PENDING_APPROVAL:
      return "info"; // Blue
    default:
      return "warning"; // Orange for all others
  }
}

function getPackageStatusLabel(status: string): string {
  switch (status) {
    case PACKAGE_STATUS.REQUESTED:
      return "Requested";
    case PACKAGE_STATUS.LICENCE_CHECKED:
      return "License Checked";
    case PACKAGE_STATUS.DOWNLOADED:
      return "Downloaded";
    case PACKAGE_STATUS.PENDING_APPROVAL:
      return "Pending Approval";
    case PACKAGE_STATUS.APPROVED:
      return "Approved";
    case PACKAGE_STATUS.REJECTED:
      return "Rejected";
    default:
      return status;
  }
}

function getLicenseStatusColor(licenseIdentifier: string, licenseStatus?: LicenseStatus) {
  if (licenseStatus) {
    switch (licenseStatus) {
      case LICENSE_STATUS.ALWAYS_ALLOWED:
      case LICENSE_STATUS.ALLOWED:
        return "success";
      case LICENSE_STATUS.AVOID:
        return "warning";
      case LICENSE_STATUS.BLOCKED:
        return "error";
      default:
        return "default";
    }
  }

  const allowedLicenses = ["MIT", "Apache-2.0", "BSD", "CC0-1.0", "Unlicense", "ISC", "0BSD"];
  const avoidLicenses = ["GPL-3.0", "LGPL-3.0"];
  const blockedLicenses = ["GPL", "GPL-2.0", "AGPL"];

  if (allowedLicenses.includes(licenseIdentifier)) {
    return "success";
  } else if (avoidLicenses.includes(licenseIdentifier)) {
    return "warning";
  } else if (blockedLicenses.includes(licenseIdentifier)) {
    return "error";
  } else {
    if (licenseIdentifier.includes("GPL-2.0") || licenseIdentifier.includes("LGPL-2.0")) {
      return "warning";
    } else if (licenseIdentifier.includes("GPL-3.0") || licenseIdentifier.includes("LGPL-3.0") || licenseIdentifier.includes("AGPL")) {
      return "error";
    } else if (licenseIdentifier.includes("MIT") || licenseIdentifier.includes("Apache-2.0") || licenseIdentifier.includes("BSD") || 
               licenseIdentifier.includes("CC0-1.0") || licenseIdentifier.includes("Unlicense") || licenseIdentifier.includes("ISC") || 
               licenseIdentifier.includes("0BSD")) {
      return "success";
    } else {
      return "default";
    }
  }
}

function getLicenseCategory(licenseIdentifier: string, licenseStatus?: LicenseStatus): string {
  if (licenseStatus) {
    switch (licenseStatus) {
      case LICENSE_STATUS.ALWAYS_ALLOWED:
      case LICENSE_STATUS.ALLOWED:
        return "Allowed";
      case LICENSE_STATUS.AVOID:
        return "Avoid";
      case LICENSE_STATUS.BLOCKED:
        return "Blocked";
      default:
        return "Review";
    }
  }

  const allowedLicenses = ["MIT", "Apache-2.0", "BSD", "CC0-1.0", "Unlicense", "ISC", "0BSD"];
  const avoidLicenses = ["GPL-3.0", "LGPL-3.0"];
  const blockedLicenses = ["GPL", "GPL-2.0", "AGPL"];

  if (allowedLicenses.includes(licenseIdentifier)) {
    return "Allowed";
  } else if (avoidLicenses.includes(licenseIdentifier)) {
    return "Avoid";
  } else if (blockedLicenses.includes(licenseIdentifier)) {
    return "Blocked";
  } else {
    if (licenseIdentifier.includes("GPL-2.0") || licenseIdentifier.includes("LGPL-2.0")) {
      return "Avoid";
    } else if (licenseIdentifier.includes("GPL-3.0") || licenseIdentifier.includes("LGPL-3.0") || licenseIdentifier.includes("AGPL")) {
      return "Blocked";
    } else if (licenseIdentifier.includes("MIT") || licenseIdentifier.includes("Apache-2.0") || licenseIdentifier.includes("BSD") || 
               licenseIdentifier.includes("CC0-1.0") || licenseIdentifier.includes("Unlicense") || licenseIdentifier.includes("ISC") || 
               licenseIdentifier.includes("0BSD")) {
      return "Allowed";
    } else {
      return "Review";
    }
  }
}
