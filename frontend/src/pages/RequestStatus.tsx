import React, { useMemo, useState } from "react";
import { useQuery } from "react-query";
import { 
  Box, 
  Typography, 
  CircularProgress, 
  Alert, 
  Chip, 
  Button, 
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  LinearProgress,
  Tooltip
} from "@mui/material";
import { MaterialReactTable, type MRT_ColumnDef } from "material-react-table";
import { Visibility, Download, Close } from "@mui/icons-material";
import { api, endpoints } from "../services/api";
import { PACKAGE_STATUS, type PackageStatus } from "../types/status";

interface Package {
  id: number;
  name: string;
  version: string;
  status: string;
  security_score: number | null;
  license_score: number | null;
  security_scan_status: string;
  license_identifier: string | null;
  type?: "new" | "existing";
  vulnerability_count?: number;
  critical_vulnerabilities?: number;
}

interface PackageRequest {
  id: number;
  application_name: string;
  version: string;
  status: string;
  total_packages: number;
  completion_percentage: number;
  created_at: string;
  requestor: {
    id: number;
    username: string;
    full_name: string;
  };
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

// Interface for the detailed API response
interface DetailedRequestResponse {
  request: PackageRequest;
  packages: Package[];
}

// Define columns for package details table
const packageColumns: MRT_ColumnDef<Package>[] = [
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
    size: 120,
    Cell: ({ row }) => {
      const pkg = row.original;
      return pkg.license_identifier ? (
        <Tooltip title={`${pkg.license_identifier} - ${getLicenseCategory(pkg.license_identifier)}`}>
          <Chip
            label={pkg.license_identifier}
            color={getLicenseStatusColor(pkg.license_identifier)}
            size="small"
          />
        </Tooltip>
      ) : (
        <Tooltip title="Unknown License - No license information available">
          <Chip
            label="Unknown"
            color="default"
            size="small"
          />
        </Tooltip>
      );
    },
  },
  {
    accessorKey: "security_score",
    header: "Security Score",
    size: 120,
    Cell: ({ row }) => {
      const score = row.original.security_score;
      return score !== null ? (
        <Chip
          label={`${score}/100`}
          color={getScoreColor(score)}
          size="small"
        />
      ) : (
        "N/A"
      );
    },
  },
  {
    accessorKey: "vulnerability_count",
    header: "Vulnerabilities",
    size: 120,
    Cell: ({ row }) => {
      const pkg = row.original;
      const vulnerabilityCount = pkg.vulnerability_count || 0;
      const criticalCount = pkg.critical_vulnerabilities || 0;
      
      return vulnerabilityCount > 0 ? (
        <Box>
          <Typography variant="body2" color="error">
            {vulnerabilityCount} total
          </Typography>
          {criticalCount > 0 && (
            <Typography variant="caption" color="error">
              {criticalCount} critical
            </Typography>
          )}
        </Box>
      ) : (
        <Typography variant="body2" color="success">
          None
        </Typography>
      );
    },
  },
  {
    accessorKey: "type",
    header: "Type",
    size: 120,
    Cell: ({ row }) => {
      const type = row.original.type;
      return type === "existing" ? (
        <Chip
          label="Already Processed"
          color="success"
          size="small"
          variant="outlined"
        />
      ) : (
        <Chip
          label="New"
          color="primary"
          size="small"
          variant="outlined"
        />
      );
    },
  },
];

export default function RequestStatus() {
  const [selectedRequest, setSelectedRequest] = useState<DetailedRequestResponse | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  const {
    data: requests,
    isLoading,
    error,
  } = useQuery<PackageRequest[]>("packageRequests", async () => {
    const response = await api.get(endpoints.packages.requests);
    return response.data.requests;
  });

  const handleViewDetails = async (requestId: number) => {
    // Open modal immediately
    setDetailsOpen(true);
    setSelectedRequest(null); // Show loading state
    
    try {
      // Fetch detailed request information with packages
      const response = await api.get(endpoints.packages.request(requestId));
      setSelectedRequest(response.data);
    } catch (error) {
      console.error('Failed to fetch request details:', error);
      // Keep modal open but with null data to show error state
      setSelectedRequest(null);
    }
  };

  const handleDownloadPackageLock = (requestId: number) => {
    // TODO: Implement package-lock download
    console.log("Download package-lock for request:", requestId);
  };

  const handleCloseDetails = () => {
    setDetailsOpen(false);
    setSelectedRequest(null);
  };

  // Transform data for the table - now showing requests instead of individual packages
  const tableData = useMemo(() => {
    if (!requests) return [];

    return requests.map((request) => ({
      id: request.id,
      requestId: request.id,
      applicationName: request.application_name,
      applicationVersion: request.version,
      requestorName: request.requestor.full_name || request.requestor.username,
      requestorUsername: request.requestor.username,
      status: request.status,
      progress: `${Math.round((request.completion_percentage / 100) * request.total_packages)}/${request.total_packages}`,
      createdAt: request.created_at,
      updatedAt: request.created_at, // Use created_at since updated_at is not in new structure
      totalPackages: request.total_packages,
      validatedPackages: Math.round((request.completion_percentage / 100) * request.total_packages),
      packages: request.packages || [],
    }));
  }, [requests]);

  // Define columns for package request rows
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
        accessorKey: "status",
        header: "Status",
        size: 120,
        Cell: ({ row }) => (
          <Chip
            label={getRequestStatusLabel(row.original.status)}
            color={getRequestStatusColor(row.original.status)}
            size="small"
          />
        ),
      },
      {
        accessorKey: "progress",
        header: "Progress",
        size: 120,
        Cell: ({ row }) => {
          const { validatedPackages, totalPackages } = row.original;
          const isComplete = validatedPackages === totalPackages;
          const progressColor = isComplete ? "success.main" : "warning.main";
          
          return (
            <Box>
              <Typography variant="body2" sx={{ fontWeight: "medium", color: progressColor }}>
                {row.original.progress}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                packages processed
              </Typography>
            </Box>
          );
        },
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
        accessorKey: "updatedAt",
        header: "Last Updated",
        size: 150,
        Cell: ({ row }) => (
          <Box>
            <Typography variant="body2">
              {new Date(row.original.updatedAt).toLocaleDateString()}
            </Typography>
            <Typography variant="caption" color="textSecondary">
              {new Date(row.original.updatedAt).toLocaleTimeString()}
            </Typography>
          </Box>
        ),
      },
      {
        id: "actions",
        header: "Actions",
        size: 100,
        Cell: ({ row }) => (
          <Box display="flex" gap={1}>
            <IconButton
              size="small"
              onClick={() => handleViewDetails(row.original.requestId)}
              title="View Details"
            >
              <Visibility fontSize="small" />
            </IconButton>
            <IconButton
              size="small"
              onClick={() => handleDownloadPackageLock(row.original.requestId)}
              title="Download Package Lock"
            >
              <Download fontSize="small" />
            </IconButton>
          </Box>
        ),
      },
    ],
    []
  );

  if (isLoading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="50vh"
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        Failed to load package requests. Please try again.
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Request Status
      </Typography>

      <Typography variant="body1" color="textSecondary" paragraph>
        Track the status of your package processing requests and view detailed
        information about each package.
      </Typography>

      {tableData.length > 0 ? (
        <MaterialReactTable
          columns={columns}
          data={tableData}
          enableColumnFilters
          enableGlobalFilter
          enableRowSelection
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
            No requests found
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Start by uploading a package-lock.json file to create your first
            processing request.
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
              Package Details {selectedRequest ? `- ID #${selectedRequest.request.id}` : '- Loading...'}
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
                <Box display="grid" gridTemplateColumns="repeat(3, 1fr)" gap={2}>
                  <Box>
                    <Typography variant="caption" color="textSecondary">
                      Application
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                      {selectedRequest.request.application_name} v{selectedRequest.request.version}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="textSecondary">
                      Requestor
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                      {selectedRequest.request.requestor.full_name} (@{selectedRequest.request.requestor.username})
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="textSecondary">
                      Status
                    </Typography>
                    <Box sx={{ mt: 0.5 }}>
                      <Chip
                        label={getRequestStatusLabel(selectedRequest.request.status)}
                        color={getRequestStatusColor(selectedRequest.request.status)}
                        size="small"
                      />
                    </Box>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="textSecondary">
                      Created
                    </Typography>
                    <Typography variant="body2">
                      {new Date(selectedRequest.request.created_at).toLocaleString()}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="textSecondary">
                      Progress
                    </Typography>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                        {Math.round((selectedRequest.request.completion_percentage / 100) * selectedRequest.request.total_packages)}/{selectedRequest.request.total_packages} packages
                      </Typography>
                      <LinearProgress 
                        variant="determinate" 
                        value={selectedRequest.request.completion_percentage}
                        sx={{ mt: 0.5 }}
                      />
                    </Box>
                  </Box>
                </Box>
              </Box>

              {/* Packages Table */}
              <Typography variant="h6" gutterBottom>
                Packages ({selectedRequest.packages.length})
              </Typography>
              
              <MaterialReactTable
                columns={packageColumns}
                data={selectedRequest.packages}
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
                    { id: "version", desc: false }
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

function getRequestStatusColor(
  status: string
):
  | "default"
  | "primary"
  | "secondary"
  | "error"
  | "info"
  | "success"
  | "warning" {
  switch (status) {
    case PACKAGE_STATUS.REQUESTED:
      return "default";
    case PACKAGE_STATUS.LICENCE_CHECKED:
      return "info";
    case PACKAGE_STATUS.DOWNLOADED:
      return "info";
    case PACKAGE_STATUS.PENDING_APPROVAL:
      return "warning";
    case PACKAGE_STATUS.APPROVED:
      return "success";
    case PACKAGE_STATUS.REJECTED:
      return "error";
    default:
      return "default";
  }
}

function getRequestStatusLabel(status: string): string {
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

function getPackageStatusColor(
  status: string
):
  | "default"
  | "primary"
  | "secondary"
  | "error"
  | "info"
  | "success"
  | "warning" {
  switch (status) {
    case PACKAGE_STATUS.REQUESTED:
      return "default";
    case PACKAGE_STATUS.LICENCE_CHECKED:
      return "info";
    case PACKAGE_STATUS.DOWNLOADED:
      return "info";
    case PACKAGE_STATUS.PENDING_APPROVAL:
      return "warning";
    case PACKAGE_STATUS.APPROVED:
      return "success";
    case PACKAGE_STATUS.REJECTED:
      return "error";
    default:
      return "default";
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

function getLicenseStatusColor(
  licenseIdentifier: string
):
  | "default"
  | "primary"
  | "secondary"
  | "error"
  | "info"
  | "success"
  | "warning" {
  // Always allowed licenses
  if (['MIT', 'BSD', 'Apache-2.0'].includes(licenseIdentifier)) {
    return "success";
  }
  
  // Allowed licenses
  if (['LGPL', 'MPL', 'CC0-1.0', 'Unlicense'].includes(licenseIdentifier)) {
    return "info";
  }
  
  // Avoid licenses
  if (['WTFPL', 'GPL-3.0', 'LGPL-3.0'].includes(licenseIdentifier)) {
    return "warning";
  }
  
  // Blocked licenses
  if (['GPL', 'GPL-2.0', 'AGPL'].includes(licenseIdentifier)) {
    return "error";
  }
  
  // Unknown licenses
  return "default";
}

function getLicenseCategory(licenseIdentifier: string): string {
  // Always allowed licenses
  if (['MIT', 'BSD', 'Apache-2.0'].includes(licenseIdentifier)) {
    return "Always Allowed";
  }
  
  // Allowed licenses
  if (['LGPL', 'MPL', 'CC0-1.0', 'Unlicense'].includes(licenseIdentifier)) {
    return "Allowed";
  }
  
  // Avoid licenses
  if (['WTFPL', 'GPL-3.0', 'LGPL-3.0'].includes(licenseIdentifier)) {
    return "Avoid";
  }
  
  // Blocked licenses
  if (['GPL', 'GPL-2.0', 'AGPL'].includes(licenseIdentifier)) {
    return "Blocked";
  }
  
  // Unknown licenses
  return "Unknown Category";
}

function getScoreColor(
  score: number
):
  | "default"
  | "primary"
  | "secondary"
  | "error"
  | "info"
  | "success"
  | "warning" {
  if (score >= 80) return "success";
  if (score >= 60) return "warning";
  return "error";
}
