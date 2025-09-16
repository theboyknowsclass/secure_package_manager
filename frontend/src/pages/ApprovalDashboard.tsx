import React, { useMemo, useState } from "react";
import { useQuery } from "react-query";
import {
  Box,
  Typography,
  Paper,
  Button,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  LinearProgress,
  Tooltip,
  Alert,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Card,
  CardContent,
} from "@mui/material";
import { MaterialReactTable, type MRT_ColumnDef } from "material-react-table";
import { 
  Visibility, 
  CheckCircle, 
  Cancel, 
  Close,
  Approval,
  Warning
} from "@mui/icons-material";
import { api, endpoints } from "../services/api";
import { 
  PACKAGE_STATUS, 
  LICENSE_STATUS,
  type PackageStatus,
  type LicenseStatus,
  isPendingApprovalStatus
} from "../types/status";

interface Package {
  id: number;
  name: string;
  version: string;
  status: PackageStatus;
  security_score: number | null;
  license_identifier: string | null;
  license_status?: LicenseStatus;
  license_score?: number;
  validation_errors: string[];
  type?: "new" | "existing";
  vulnerability_count?: number;
  critical_vulnerabilities?: number;
  selected?: boolean;
  onSelectChange?: (selected: boolean) => void;
}

interface PackageRequest {
  id: number;
  status: PackageStatus;
  total_packages: number;
  validated_packages: number;
  created_at: string;
  updated_at: string;
  requestor: {
    id: number;
    username: string;
    full_name: string;
  };
  application: {
    name: string;
    version: string;
  };
  packages: Package[];
}

// Define columns for package details table
const packageColumns: MRT_ColumnDef<Package>[] = [
  {
    accessorKey: "select",
    header: "Select",
    size: 60,
    Cell: ({ row }) => (
      <input
        type="checkbox"
        checked={row.original.selected || false}
        onChange={(e) => {
          // This will be handled by the parent component
          if (row.original.onSelectChange) {
            row.original.onSelectChange(e.target.checked);
          }
        }}
      />
    ),
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
        // Remove parentheses and split by OR and AND, then clean up
        return expression
          .replace(/[()]/g, '') // Remove parentheses
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
              color={getLicenseStatusColor(license, pkg.license_status)}
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

export default function ApprovalDashboard() {
  const [selectedRequest, setSelectedRequest] = useState<PackageRequest | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [approvalReason, setApprovalReason] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedPackages, setSelectedPackages] = useState<Set<number>>(new Set());

  const {
    data: requests,
    isLoading,
    error,
    refetch,
  } = useQuery<PackageRequest[]>("approvalRequests", async () => {
    const response = await api.get(endpoints.packages.requests);
    return response.data.requests;
  });

  const handleViewDetails = (requestId: number) => {
    // Open modal immediately
    setDetailsOpen(true);
    
    // Find and set the request data
    const request = requests?.find(r => r.id === requestId);
    if (request) {
      setSelectedRequest(request);
    } else {
      // If request not found, close modal
      setDetailsOpen(false);
    }
  };

  const handleCloseDetails = () => {
    setDetailsOpen(false);
    setSelectedRequest(null);
    setApprovalReason("");
    setRejectionReason("");
    setSelectedPackages(new Set());
  };

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
      .filter(pkg => pkg.status === "pending_approval")
      .map(pkg => pkg.id);
    
    if (selected) {
      setSelectedPackages(new Set(pendingPackageIds));
    } else {
      setSelectedPackages(new Set());
    }
  };

  const getLicenseSummary = (packages: Package[]) => {
    const licenseCounts: { [key: string]: number } = {};
    const licenseCategories: { [key: string]: string } = {};
    
    const categorizeLicense = (licenseExpression: string): string => {
      // Handle complex license expressions with OR/AND
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
      
      // If it contains OR and has allowed options, it's generally acceptable
      if (licenseExpression.includes(" OR ") && hasAllowed && !hasBlocked) {
        return "Allowed";
      }
      
      // If it contains AND, it's more restrictive
      if (licenseExpression.includes(" AND ")) {
        if (hasBlocked) return "Blocked";
        if (hasAvoid) return "Avoid";
        return "Review";
      }
      
      // Single license categorization
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

  const handleApproveRequest = async () => {
    if (!selectedRequest || selectedPackages.size === 0) return;
    
    setIsProcessing(true);
    try {
      // Approve only selected packages
      for (const packageId of selectedPackages) {
        await api.post(`/api/admin/packages/approve/${packageId}`, {
          reason: approvalReason || "Approved by administrator"
        });
      }
      
      // Refresh data
      await refetch();
      handleCloseDetails();
      
    } catch (error) {
      console.error("Error approving packages:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRejectRequest = async () => {
    if (!selectedRequest || selectedPackages.size === 0) return;
    
    setIsProcessing(true);
    try {
      // Reject only selected packages
      for (const packageId of selectedPackages) {
        await api.post(`/api/admin/packages/reject/${packageId}`, {
          reason: rejectionReason || "Rejected by administrator"
        });
      }
      
      // Refresh data
      await refetch();
      handleCloseDetails();
      
    } catch (error) {
      console.error("Error rejecting packages:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  // Filter requests that have packages pending approval
  const approvalRequests = useMemo(() => {
    if (!requests) return [];
    
    return requests.filter(request => 
      request.packages.some(pkg => 
        isPendingApprovalStatus(pkg.status)
      )
    );
  }, [requests]);

  // Transform data for the table
  const tableData = useMemo(() => {
    return approvalRequests.map((request) => {
      const pendingPackages = request.packages.filter(pkg => pkg.status === PACKAGE_STATUS.PENDING_APPROVAL);
      const approvedPackages = request.packages.filter(pkg => pkg.status === PACKAGE_STATUS.APPROVED);
      const rejectedPackages = request.packages.filter(pkg => pkg.status === PACKAGE_STATUS.REJECTED);
      const processingPackages = request.packages.filter(pkg => 
        ![PACKAGE_STATUS.PENDING_APPROVAL, PACKAGE_STATUS.APPROVED, PACKAGE_STATUS.REJECTED].includes(pkg.status)
      );
      
      return {
        id: request.id,
        requestId: request.id,
        applicationName: request.application.name,
        applicationVersion: request.application.version,
        requestorName: request.requestor.full_name || request.requestor.username,
        requestorUsername: request.requestor.username,
        status: request.status,
        processingCount: processingPackages.length,
        pendingCount: pendingPackages.length,
        approvedCount: approvedPackages.length,
        rejectedCount: rejectedPackages.length,
        createdAt: request.created_at,
        updatedAt: request.updated_at,
        totalPackages: request.total_packages,
        packages: request.packages || [],
      };
    });
  }, [approvalRequests]);

  // Define columns for approval request rows
  const columns = useMemo<MRT_ColumnDef<any>[]>(
    () => [
      {
        accessorKey: "requestId",
        header: "ID",
        size: 100,
        Cell: ({ row }) => (
          <Typography variant="body2" sx={{ fontWeight: "medium" }}>
            #{row.original.requestId}
          </Typography>
        ),
      },
      {
        accessorKey: "applicationName",
        header: "Application",
        size: 200,
        Cell: ({ row }) => (
          <Box>
            <Typography variant="body2" sx={{ fontWeight: "medium" }}>
              {row.original.applicationName}
            </Typography>
            <Typography variant="caption" color="textSecondary">
              v{row.original.applicationVersion}
            </Typography>
          </Box>
        ),
      },
      {
        accessorKey: "requestorName",
        header: "Requestor",
        size: 150,
        Cell: ({ row }) => (
          <Box>
            <Typography variant="body2" sx={{ fontWeight: "medium" }}>
              {row.original.requestorName}
            </Typography>
            <Typography variant="caption" color="textSecondary">
              @{row.original.requestorUsername}
            </Typography>
          </Box>
        ),
      },
      {
        accessorKey: "processingCount",
        header: "Processing",
        size: 100,
        Cell: ({ row }) => {
          const { processingCount, totalPackages } = row.original;
          const isAllProcessed = processingCount === 0;
          
          if (isAllProcessed) {
            return (
              <Box>
                <Tooltip title={`${totalPackages} processed`}>
                  <Chip
                    label={totalPackages.toString()}
                    color="success"
                    size="small"
                    icon={<CheckCircle />}
                  />
                </Tooltip>
                <Typography variant="caption" color="textSecondary" sx={{ display: "block", mt: 0.5 }}>
                  processed
                </Typography>
              </Box>
            );
          } else {
            return (
              <Box>
                <Tooltip title={`${processingCount} of ${totalPackages} processing`}>
                  <Chip
                    label={`${processingCount}/${totalPackages}`}
                    color="warning"
                    size="small"
                    icon={<CircularProgress size={16} />}
                  />
                </Tooltip>
                <Typography variant="caption" color="textSecondary" sx={{ display: "block", mt: 0.5 }}>
                  processing
                </Typography>
              </Box>
            );
          }
        },
      },
      {
        accessorKey: "pendingCount",
        header: "Pending Approval",
        size: 120,
        Cell: ({ row }) => (
          <Box>
            <Tooltip title={`${row.original.pendingCount} pending approval`}>
              <Chip
                label={row.original.pendingCount.toString()}
                color="warning"
                size="small"
                icon={<Warning />}
              />
            </Tooltip>
            <Typography variant="caption" color="textSecondary" sx={{ display: "block", mt: 0.5 }}>
              pending
            </Typography>
          </Box>
        ),
      },
      {
        accessorKey: "createdAt",
        header: "Created",
        size: 150,
        Cell: ({ row }) => (
          <Box>
            <Typography variant="body2">
              {new Date(row.original.createdAt).toLocaleDateString()}
            </Typography>
            <Typography variant="caption" color="textSecondary">
              {new Date(row.original.createdAt).toLocaleTimeString()}
            </Typography>
          </Box>
        ),
      },
      {
        accessorKey: "actions",
        header: "Actions",
        size: 100,
        Cell: ({ row }) => (
          <Box display="flex" gap={1}>
            <Tooltip title="View Details">
              <IconButton
                size="small"
                onClick={() => handleViewDetails(row.original.requestId)}
              >
                <Visibility fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        ),
      },
    ],
    []
  );

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        Error loading approval requests: {error.message}
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Approval Dashboard
      </Typography>
      <Typography variant="body1" color="textSecondary" paragraph>
        Review and approve package requests that have completed security scanning.
      </Typography>

      {tableData.length > 0 ? (
        <MaterialReactTable
          columns={columns}
          data={tableData}
          enableColumnFilters
          enableGlobalFilter
          enableSorting
          enableColumnResizing
          enablePagination={false}
          muiTableProps={{
            sx: {
              tableLayout: "fixed",
            },
          }}
          muiTableContainerProps={{
            sx: {
              maxHeight: "70vh",
            },
          }}
          initialState={{
            density: "compact",
            showColumnFilters: true,
            sorting: [{ id: "createdAt", desc: true }], // Sort by newest first
          }}
        />
      ) : (
        <Box sx={{ p: 3, textAlign: "center" }}>
          <Typography variant="h6" color="textSecondary">
            No requests pending approval
          </Typography>
          <Typography variant="body2" color="textSecondary">
            All package requests have been processed or are still being scanned.
          </Typography>
        </Box>
      )}

      {/* Package Details Modal */}
      <Dialog 
        open={detailsOpen} 
        onClose={handleCloseDetails}
        maxWidth="lg"
        fullWidth
        sx={{ zIndex: 9999 }}
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">
              Package Approval {selectedRequest ? `- ID #${selectedRequest.id}` : '- Loading...'}
            </Typography>
            <IconButton onClick={handleCloseDetails} size="small">
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
                      {selectedRequest.application.name} v{selectedRequest.application.version}
                    </Typography>
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="caption" color="textSecondary">
                      Requestor
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                      {selectedRequest.requestor.full_name} (@{selectedRequest.requestor.username})
                    </Typography>
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="caption" color="textSecondary">
                      Created
                    </Typography>
                    <Typography variant="body2">
                      {new Date(selectedRequest.created_at).toLocaleString()}
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
                  
                  // Parse complex license expressions and create individual license counts
                  const individualLicenseCounts: { [key: string]: number } = {};
                  
                  Object.entries(licenseCounts).forEach(([licenseExpression, count]) => {
                    // Parse the license expression to get individual licenses
                    const individualLicenses = licenseExpression
                      .replace(/[()]/g, '') // Remove parentheses
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
                      {selectedPackages.size} of {selectedRequest.packages.filter(p => p.status === "pending_approval").length} selected
                    </Typography>
                    <Button
                      size="small"
                      onClick={() => handleSelectAll(true)}
                      disabled={selectedPackages.size === selectedRequest.packages.filter(p => p.status === "pending_approval").length}
                    >
                      Select All
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
                          disabled={isProcessing || selectedPackages.size === 0}
                          sx={{ mt: 2 }}
                        >
                          Approve Selected ({selectedPackages.size})
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
                          disabled={isProcessing || !rejectionReason.trim() || selectedPackages.size === 0}
                          sx={{ mt: 2 }}
                        >
                          Reject Selected ({selectedPackages.size})
                        </Button>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </Box>

              {/* Packages Table */}
              <Typography variant="h6" gutterBottom>
                Packages ({selectedRequest.packages.length})
              </Typography>
              
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
          <Button onClick={handleCloseDetails}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

// Helper functions
function getRequestStatusColor(status: string) {
  switch (status) {
    case "requested":
      return "default";
    case "performing_licence_check":
      return "warning";
    case "licence_check_complete":
      return "info";
    case "performing_security_scan":
      return "warning";
    case "security_scan_complete":
      return "info";
    case "pending_approval":
      return "warning";
    case "approved":
      return "success";
    case "rejected":
      return "error";
    default:
      return "default";
  }
}

function getRequestStatusLabel(status: string): string {
  switch (status) {
    case "requested":
      return "Requested";
    case "performing_licence_check":
      return "Checking Licenses";
    case "licence_check_complete":
      return "License Check Complete";
    case "performing_security_scan":
      return "Scanning Security";
    case "security_scan_complete":
      return "Security Scan Complete";
    case "pending_approval":
      return "Pending Approval";
    case "approved":
      return "Approved";
    case "rejected":
      return "Rejected";
    default:
      return status;
  }
}

function getPackageStatusColor(status: string) {
  switch (status) {
    case "requested":
      return "default";
    case "performing_licence_check":
      return "warning";
    case "licence_check_complete":
      return "info";
    case "performing_security_scan":
      return "warning";
    case "security_scan_complete":
      return "info";
    case "pending_approval":
      return "warning";
    case "approved":
      return "success";
    case "rejected":
      return "error";
    default:
      return "default";
  }
}

function getPackageStatusLabel(status: string): string {
  switch (status) {
    case "requested":
      return "Requested";
    case "performing_licence_check":
      return "Checking License";
    case "licence_check_complete":
      return "License OK";
    case "performing_security_scan":
      return "Scanning";
    case "security_scan_complete":
      return "Scan Complete";
    case "pending_approval":
      return "Pending Approval";
    case "approved":
      return "Approved";
    case "rejected":
      return "Rejected";
    default:
      return status;
  }
}

function getLicenseStatusColor(licenseIdentifier: string, licenseStatus?: LicenseStatus) {
  // Use database license status if available
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

  // Fallback to hardcoded logic if no database status
  const allowedLicenses = ["MIT", "Apache-2.0", "BSD", "CC0-1.0", "Unlicense", "ISC", "0BSD"];
  const avoidLicenses = ["GPL-3.0", "LGPL-3.0"];
  const blockedLicenses = ["GPL", "GPL-2.0", "AGPL"];

  // Check for exact matches first
  if (allowedLicenses.includes(licenseIdentifier)) {
    return "success";
  } else if (avoidLicenses.includes(licenseIdentifier)) {
    return "warning";
  } else if (blockedLicenses.includes(licenseIdentifier)) {
    return "error";
  } else {
    // Check for partial matches (e.g., "GPL-2.0" should match "GPL")
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
  // Use database license status if available
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

  // Fallback to hardcoded logic if no database status
  const allowedLicenses = ["MIT", "Apache-2.0", "BSD", "CC0-1.0", "Unlicense", "ISC", "0BSD"];
  const avoidLicenses = ["GPL-3.0", "LGPL-3.0"];
  const blockedLicenses = ["GPL", "GPL-2.0", "AGPL"];

  // Check for exact matches first
  if (allowedLicenses.includes(licenseIdentifier)) {
    return "Allowed";
  } else if (avoidLicenses.includes(licenseIdentifier)) {
    return "Avoid";
  } else if (blockedLicenses.includes(licenseIdentifier)) {
    return "Blocked";
  } else {
    // Check for partial matches
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
