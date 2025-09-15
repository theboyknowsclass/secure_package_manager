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

interface Package {
  id: number;
  name: string;
  version: string;
  status: string;
  security_score: number | null;
  license_identifier: string | null;
  validation_errors: string[];
  type?: "new" | "existing";
}

interface PackageRequest {
  id: number;
  status: string;
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

export default function PackageRequests() {
  const [selectedRequest, setSelectedRequest] = useState<PackageRequest | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  const {
    data: requests,
    isLoading,
    error,
  } = useQuery<PackageRequest[]>("packageRequests", async () => {
    const response = await api.get(endpoints.packages.requests);
    return response.data.requests;
  });

  const handleViewDetails = (requestId: number) => {
    const request = requests?.find(r => r.id === requestId);
    if (request) {
      setSelectedRequest(request);
      setDetailsOpen(true);
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
      applicationName: request.application.name,
      applicationVersion: request.application.version,
      requestorName: request.requestor.full_name || request.requestor.username,
      requestorUsername: request.requestor.username,
      status: request.status,
      progress: `${request.validated_packages}/${request.total_packages}`,
      createdAt: request.created_at,
      updatedAt: request.updated_at,
      totalPackages: request.total_packages,
      validatedPackages: request.validated_packages,
      packages: request.packages || [],
    }));
  }, [requests]);

  // Define columns for package request rows
  const columns = useMemo<MRT_ColumnDef<any>[]>(
    () => [
      {
        accessorKey: "requestId",
        header: "Request ID",
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
            label={row.original.status}
            color={getRequestStatusColor(row.original.status)}
            size="small"
          />
        ),
      },
      {
        accessorKey: "progress",
        header: "Progress",
        size: 120,
        Cell: ({ row }) => (
          <Box>
            <Typography variant="body2" sx={{ fontWeight: "medium" }}>
              {row.original.progress}
            </Typography>
            <Typography variant="caption" color="textSecondary">
              packages validated
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
        Package Status
      </Typography>

      <Typography variant="body1" color="textSecondary" paragraph>
        Track the status of your package validation requests and view detailed
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
            pagination: { pageSize: 10, pageIndex: 0 },
            sorting: [{ id: "createdAt", desc: true }], // Sort by newest first
          }}
        />
      ) : (
        <Box sx={{ p: 3, textAlign: "center" }}>
          <Typography variant="h6" color="textSecondary">
            No package requests found
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Start by uploading a package-lock.json file to create your first
            request.
          </Typography>
        </Box>
      )}

      {/* Package Details Modal */}
      <Dialog 
        open={detailsOpen} 
        onClose={handleCloseDetails}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">
              Package Details - Request #{selectedRequest?.id}
            </Typography>
            <IconButton onClick={handleCloseDetails} size="small">
              <Close />
            </IconButton>
          </Box>
        </DialogTitle>
        
        <DialogContent>
          {selectedRequest && (
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
                      {selectedRequest.application.name} v{selectedRequest.application.version}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="textSecondary">
                      Requestor
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                      {selectedRequest.requestor.full_name} (@{selectedRequest.requestor.username})
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="textSecondary">
                      Status
                    </Typography>
                    <Chip
                      label={selectedRequest.status}
                      color={getRequestStatusColor(selectedRequest.status)}
                      size="small"
                    />
                  </Box>
                  <Box>
                    <Typography variant="caption" color="textSecondary">
                      Created
                    </Typography>
                    <Typography variant="body2">
                      {new Date(selectedRequest.created_at).toLocaleString()}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="textSecondary">
                      Progress
                    </Typography>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                        {selectedRequest.validated_packages}/{selectedRequest.total_packages} packages
                      </Typography>
                      <LinearProgress 
                        variant="determinate" 
                        value={(selectedRequest.validated_packages / selectedRequest.total_packages) * 100}
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
              
              <TableContainer component={Paper} sx={{ maxHeight: 400 }}>
                <Table stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>Package</TableCell>
                      <TableCell>Version</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>License</TableCell>
                      <TableCell>Security Score</TableCell>
                      <TableCell>Vulnerabilities</TableCell>
                      <TableCell>Type</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {selectedRequest.packages.map((pkg) => (
                      <TableRow key={pkg.id}>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                            {pkg.name}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {pkg.version}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={pkg.status}
                            color={getPackageStatusColor(pkg.status)}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          {pkg.license_identifier ? (
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
                          )}
                        </TableCell>
                        <TableCell>
                          {pkg.security_score !== null ? (
                            <Chip
                              label={`${pkg.security_score}/100`}
                              color={getScoreColor(pkg.security_score)}
                              size="small"
                            />
                          ) : (
                            "N/A"
                          )}
                        </TableCell>
                        <TableCell>
                          {pkg.vulnerability_count > 0 ? (
                            <Box>
                              <Typography variant="body2" color="error">
                                {pkg.vulnerability_count} total
                              </Typography>
                              {pkg.critical_vulnerabilities > 0 && (
                                <Typography variant="caption" color="error">
                                  {pkg.critical_vulnerabilities} critical
                                </Typography>
                              )}
                            </Box>
                          ) : (
                            <Typography variant="body2" color="success">
                              None
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          {pkg.type === "existing" ? (
                            <Chip
                              label="Already Validated"
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
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
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
    case "requested":
      return "primary";
    case "processing":
      return "warning";
    case "completed":
      return "success";
    case "failed":
      return "error";
    case "cancelled":
      return "default";
    default:
      return "default";
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
    case "requested":
      return "primary";
    case "downloading":
      return "info";
    case "downloaded":
      return "info";
    case "validating":
      return "warning";
    case "validated":
      return "success";
    case "already_validated":
      return "success";
    case "failed":
      return "error";
    case "approved":
      return "info";
    case "published":
      return "success";
    case "rejected":
      return "error";
    default:
      return "default";
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
