import React from "react";
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
  Tooltip
} from "@mui/material";
import { MaterialReactTable, type MRT_ColumnDef } from "material-react-table";
import { Close } from "@mui/icons-material";
import { api, endpoints } from "../services/api";
import { PACKAGE_STATUS, type PackageStatus, type Package, type PackageRequest, type DetailedRequestResponse } from "../types/status";


interface RequestDetailDialogProps {
  open: boolean;
  onClose: () => void;
  requestId: number | null;
  selectedRequest: DetailedRequestResponse | null;
  onRequestLoaded: (request: DetailedRequestResponse) => void;
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
      const count = row.original.vulnerability_count;
      const critical = row.original.critical_vulnerabilities;
      
      if (count === null || count === undefined) {
        return <Typography variant="body2" color="textSecondary">-</Typography>;
      }
      
      if (count === 0) {
        return <Typography variant="body2" color="success.main">None</Typography>;
      }
      
      return (
        <Box>
          <Typography variant="body2" color="error.main">
            {count} total
          </Typography>
          {critical && critical > 0 && (
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
    Cell: ({ row }) => {
      const type = row.original.type;
      return type ? (
        <Chip
          label={type === "new" ? "New" : "Existing"}
          color={type === "new" ? "primary" : "default"}
          size="small"
        />
      ) : (
        <Typography variant="body2" color="textSecondary">-</Typography>
      );
    },
  },
];

export default function RequestDetailDialog({
  open,
  onClose,
  requestId,
  selectedRequest,
  onRequestLoaded,
}: RequestDetailDialogProps) {
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (open && requestId && !selectedRequest) {
      setLoading(true);
      // Fetch detailed request information with packages
      api.get(endpoints.packages.request(requestId))
        .then(response => {
          onRequestLoaded(response.data);
        })
        .catch(error => {
          console.error('Failed to fetch request details:', error);
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [open, requestId, selectedRequest, onRequestLoaded]);

  const handleClose = () => {
    onClose();
  };

  return (
    <Dialog 
      open={open} 
      onClose={handleClose}
      maxWidth="lg"
      fullWidth
      sx={{ zIndex: 9999 }}
    >
      <DialogTitle sx={{ p: 0 }}>
        <Box display="flex" justifyContent="flex-end" alignItems="center">
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
                  <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                    {new Date(selectedRequest.request.created_at).toLocaleString()}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="textSecondary">
                    Progress
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                    {selectedRequest.packages.length} packages
                  </Typography>
                </Box>
              </Box>
            </Box>

            {/* Package Details Table */}
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
        ) : loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
            <CircularProgress />
            <Typography variant="body2" sx={{ ml: 2 }}>
              Loading package details...
            </Typography>
          </Box>
        ) : (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
            <Typography variant="body2" color="textSecondary">
              Failed to load request details
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
    case "pending_approval":
      return "warning";
    case "approved":
      return "success";
    case "rejected":
      return "error";
    case "processing":
      return "info";
    default:
      return "default";
  }
}

function getRequestStatusLabel(status: string): string {
  switch (status) {
    case "pending_approval":
      return "Pending Approval";
    case "approved":
      return "Approved";
    case "rejected":
      return "Rejected";
    case "processing":
      return "Processing";
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
