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
  Tooltip
} from "@mui/material";
import { MaterialReactTable, type MRT_ColumnDef } from "material-react-table";
import { Visibility, Download } from "@mui/icons-material";
import { api, endpoints } from "../services/api";
import { PACKAGE_STATUS, type PackageStatus, type Package, type PackageRequest, type DetailedRequestResponse } from "../types/status";
import RequestDetailDialog from "../components/RequestDetailDialog";


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
        <Tooltip title={`${pkg.license_identifier} - ${getLicenseCategoryFromScore(pkg.license_score)}`}>
          <Chip
            label={pkg.license_identifier}
            color={getLicenseColorFromScore(pkg.license_score)}
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
      const scanStatus = row.original.security_scan_status;
      
      if (score !== null) {
        return (
          <Chip
            label={`${score}/100`}
            color={getScoreColor(score)}
            size="small"
          />
        );
      } else if (scanStatus === "failed") {
        return (
          <Tooltip title="Security scan failed">
            <Chip
              label="Scan Failed"
              color="error"
              size="small"
            />
          </Tooltip>
        );
      } else if (scanStatus === "running") {
        return (
          <Tooltip title="Security scan in progress">
            <Chip
              label="Scanning..."
              color="info"
              size="small"
            />
          </Tooltip>
        );
      } else {
        return (
          <Typography variant="body2" color="textSecondary">-</Typography>
        );
      }
    },
  },
  {
    accessorKey: "license_score",
    header: "License Score",
    size: 120,
    Cell: ({ row }) => {
      const score = row.original.license_score;
      return score !== null ? (
        <Chip
          label={`${score}/100`}
          color={getScoreColor(score)}
          size="small"
        />
      ) : (
        <Typography variant="body2" color="textSecondary">-</Typography>
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
  const [selectedRequestId, setSelectedRequestId] = useState<number | null>(null);

  const {
    data: requests,
    isLoading,
    error,
  } = useQuery<PackageRequest[]>("packageRequests", async () => {
    const response = await api.get(endpoints.packages.requests);
    return response.data.requests;
  }, {
    refetchInterval: 5000, // Poll every 5 seconds
    refetchIntervalInBackground: true, // Continue polling when tab is not active
  });

  const handleViewDetails = (requestId: number) => {
    setSelectedRequestId(requestId);
    setDetailsOpen(true);
  };

  const handleDownloadPackageLock = (requestId: number) => {
    // TODO: Implement package-lock download
    console.log("Download package-lock for request:", requestId);
  };

  const handleCloseDetails = () => {
    setDetailsOpen(false);
    setSelectedRequestId(null);
    setSelectedRequest(null);
  };

  const handleRequestLoaded = (request: DetailedRequestResponse) => {
    setSelectedRequest(request);
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

      {/* Request Detail Dialog */}
      <RequestDetailDialog
        open={detailsOpen}
        onClose={handleCloseDetails}
        requestId={selectedRequestId}
        selectedRequest={selectedRequest}
        onRequestLoaded={handleRequestLoaded}
      />
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

// Helper functions for the main table
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

function getLicenseColorFromScore(
  licenseScore: number | null
):
  | "default"
  | "primary"
  | "secondary"
  | "error"
  | "info"
  | "success"
  | "warning" {
  if (licenseScore === null) {
    return "info"; // Pending - blue
  }
  
  if (licenseScore === 0) {
    return "error"; // Blocked - red
  } else if (licenseScore >= 80) {
    return "success"; // Allowed - green
  } else if (licenseScore >= 50) {
    return "info"; // Unknown - blue
  } else if (licenseScore >= 30) {
    return "warning"; // Avoid - orange
  } else {
    return "error"; // Blocked - red
  }
}

function getLicenseCategoryFromScore(licenseScore: number | null): string {
  if (licenseScore === null) {
    return "Pending";
  }
  
  if (licenseScore === 0) {
    return "Blocked";
  } else if (licenseScore >= 80) {
    return "Allowed";
  } else if (licenseScore >= 50) {
    return "Unknown";
  } else if (licenseScore >= 30) {
    return "Avoid";
  } else {
    return "Blocked";
  }
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

