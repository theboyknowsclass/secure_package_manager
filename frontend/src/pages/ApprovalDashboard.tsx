import React, { useMemo, useState } from "react";
import { useQuery } from "react-query";
import {
  Box,
  Typography,
  Chip,
  IconButton,
  CircularProgress,
  Tooltip,
  Alert,
} from "@mui/material";
import { MaterialReactTable, type MRT_ColumnDef } from "material-react-table";
import { Visibility, CheckCircle, Warning } from "@mui/icons-material";
import { api, endpoints } from "../services/api";
import {
  PACKAGE_STATUS,
  type DetailedRequestResponse,
  type PackageRequest,
  type Package,
} from "../types/status";
import ApprovalDetailDialog from "../components/ApprovalDetailDialog";
import { getTotalVulnerabilities } from "../utils/scanUtils";

interface ApprovalRequestRowData {
  id: number;
  requestId: number;
  applicationName: string;
  applicationVersion: string;
  requestorName: string;
  requestorUsername: string;
  status: string;
  processingCount: number;
  pendingCount: number;
  approvedCount: number;
  rejectedCount: number;
  createdAt: string;
  updatedAt: string;
  totalPackages: number;
  packages: Package[];
}

// Memoized cell components for better performance
const SelectCell = React.memo(({ 
  selected, 
  onSelectChange 
}: { 
  selected: boolean; 
  onSelectChange?: (selected: boolean) => void;
}) => (
  <input
    type="checkbox"
    checked={selected}
    onChange={e => {
      if (onSelectChange) {
        onSelectChange(e.target.checked);
      }
    }}
  />
));

const PackageNameCell = React.memo(({ name }: { name: string }) => (
  <Typography variant="body2" sx={{ fontWeight: "medium" }}>
    {name}
  </Typography>
));

const VersionCell = React.memo(({ version }: { version: string }) => (
  <Typography variant="body2">{version}</Typography>
));

const StatusCell = React.memo(({ status }: { status: string }) => (
  <Chip
    label={getPackageStatusLabel(status)}
    color={getPackageStatusColor(status)}
    size="small"
  />
));

// Memoized license parsing function
const parseLicenseExpression = (expression: string): string[] => {
  return expression
    .replace(/[()]/g, "")
    .split(/\s+(?:OR|AND)\s+/i)
    .map(license => license.trim())
    .filter(license => license.length > 0);
};

const LicenseCell = React.memo(({ licenseIdentifier }: { licenseIdentifier: string | null }) => {
  if (!licenseIdentifier) {
    return (
      <Typography variant="body2" color="textSecondary">
        Unknown
      </Typography>
    );
  }

  const licenses = parseLicenseExpression(licenseIdentifier);

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
});

// Define columns for package details table
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const packageColumns: MRT_ColumnDef<
  Package & { selected?: boolean; onSelectChange?: (selected: boolean) => void }
>[] = [
  {
    accessorKey: "select",
    header: "Select",
    size: 60,
    Cell: ({ row }) => (
      <SelectCell 
        selected={row.original.selected || false}
        onSelectChange={row.original.onSelectChange}
      />
    ),
  },
  {
    accessorKey: "name",
    header: "Package",
    size: 200,
    Cell: ({ row }) => <PackageNameCell name={row.original.name} />,
  },
  {
    accessorKey: "version",
    header: "Version",
    size: 120,
    Cell: ({ row }) => <VersionCell version={row.original.version} />,
  },
  {
    accessorKey: "status",
    header: "Status",
    size: 120,
    Cell: ({ row }) => <StatusCell status={row.original.status} />,
  },
  {
    accessorKey: "license_identifier",
    header: "License",
    size: 150,
    Cell: ({ row }) => <LicenseCell licenseIdentifier={row.original.license_identifier} />,
  },
  {
    accessorKey: "security_score",
    header: "Security",
    size: 100,
    Cell: ({ row }) => {
      const score = row.original.security_score;
      if (score === null) {
        return (
          <Typography variant="body2" color="textSecondary">
            -
          </Typography>
        );
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
      const total = getTotalVulnerabilities(pkg.scan_result);
      const critical = pkg.scan_result?.critical_count || 0;

      if (total === 0) {
        return (
          <Typography variant="body2" color="success.main">
            None
          </Typography>
        );
      }

      return (
        <Box>
          <Typography
            variant="body2"
            color={critical > 0 ? "error.main" : "warning.main"}
          >
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
  const [selectedRequest, setSelectedRequest] =
    useState<DetailedRequestResponse | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  const {
    data: requests,
    isLoading,
    error,
    refetch,
  } = useQuery<PackageRequest[]>("approvalRequests", async () => {
    const response = await api.get(endpoints.packages.requests);
    return response.data.requests;
  });

  const handleViewDetails = async (requestId: number) => {
    setDetailsOpen(true);
    setSelectedRequest(null); // Show loading state

    try {
      const response = await api.get(endpoints.packages.request(requestId));
      setSelectedRequest(response.data);
    } catch (error) {
      console.error("Failed to fetch request details:", error);
      setSelectedRequest(null);
    }
  };

  const handleCloseDetails = () => {
    setDetailsOpen(false);
    setSelectedRequest(null);
  };

  const handleApprovalComplete = async () => {
    await refetch();
  };

  // Filter requests that have packages pending approval
  const approvalRequests = useMemo(() => {
    if (!requests) return [];

    return requests.filter(
      request =>
        request.package_counts && request.package_counts["Pending Approval"] > 0
    );
  }, [requests]);

  // Transform data for the table
  const tableData = useMemo(() => {
    return approvalRequests.map(request => {
      const packageCounts = request.package_counts || {};
      const pendingPackages = packageCounts["Pending Approval"] || 0;
      const approvedPackages = packageCounts["Approved"] || 0;
      const rejectedPackages = packageCounts["Rejected"] || 0;
      const processingPackages =
        request.total_packages -
        pendingPackages -
        approvedPackages -
        rejectedPackages;

      return {
        id: request.id,
        requestId: request.id,
        applicationName: request.application_name,
        applicationVersion: request.version,
        requestorName:
          request.requestor.full_name || request.requestor.username,
        requestorUsername: request.requestor.username,
        status: request.status,
        processingCount: processingPackages,
        pendingCount: pendingPackages,
        approvedCount: approvedPackages,
        rejectedCount: rejectedPackages,
        createdAt: request.created_at,
        updatedAt: request.created_at, // Use created_at since updated_at is not in new structure
        totalPackages: request.total_packages,
        packages: [], // Will be populated when details are loaded
      };
    });
  }, [approvalRequests]);

  // Define columns for approval request rows
  const columns = useMemo<MRT_ColumnDef<ApprovalRequestRowData>[]>(
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
                <Typography
                  variant="caption"
                  color="textSecondary"
                  sx={{ display: "block", mt: 0.5 }}
                >
                  processed
                </Typography>
              </Box>
            );
          } else {
            return (
              <Box>
                <Tooltip
                  title={`${processingCount} of ${totalPackages} processing`}
                >
                  <Chip
                    label={`${processingCount}/${totalPackages}`}
                    color="warning"
                    size="small"
                    icon={<CircularProgress size={16} />}
                  />
                </Tooltip>
                <Typography
                  variant="caption"
                  color="textSecondary"
                  sx={{ display: "block", mt: 0.5 }}
                >
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
            <Typography
              variant="caption"
              color="textSecondary"
              sx={{ display: "block", mt: 0.5 }}
            >
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
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 400,
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        Error loading approval requests:{" "}
        {error instanceof Error ? error.message : "Unknown error"}
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Approval Dashboard
      </Typography>
      <Typography variant="body1" color="textSecondary" paragraph>
        Review and approve package requests that have completed security
        scanning.
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
          enableVirtualization={tableData.length > 50}
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
      <ApprovalDetailDialog
        open={detailsOpen}
        onClose={handleCloseDetails}
        selectedRequest={selectedRequest}
        onApprovalComplete={handleApprovalComplete}
      />
    </Box>
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
    case PACKAGE_STATUS.SUBMITTED:
      return "Submitted";
    case PACKAGE_STATUS.PARSED:
      return "Parsed";
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

function getLicenseStatusColor(licenseIdentifier: string) {
  const allowedLicenses = [
    "MIT",
    "Apache-2.0",
    "BSD",
    "CC0-1.0",
    "Unlicense",
    "ISC",
    "0BSD",
  ];
  const avoidLicenses = ["GPL-3.0", "LGPL-3.0"];
  const blockedLicenses = ["GPL", "GPL-2.0", "AGPL"];

  if (allowedLicenses.includes(licenseIdentifier)) {
    return "success";
  } else if (avoidLicenses.includes(licenseIdentifier)) {
    return "warning";
  } else if (blockedLicenses.includes(licenseIdentifier)) {
    return "error";
  } else {
    if (
      licenseIdentifier.includes("GPL-2.0") ||
      licenseIdentifier.includes("LGPL-2.0")
    ) {
      return "warning";
    } else if (
      licenseIdentifier.includes("GPL-3.0") ||
      licenseIdentifier.includes("LGPL-3.0") ||
      licenseIdentifier.includes("AGPL")
    ) {
      return "error";
    } else if (
      licenseIdentifier.includes("MIT") ||
      licenseIdentifier.includes("Apache-2.0") ||
      licenseIdentifier.includes("BSD") ||
      licenseIdentifier.includes("CC0-1.0") ||
      licenseIdentifier.includes("Unlicense") ||
      licenseIdentifier.includes("ISC") ||
      licenseIdentifier.includes("0BSD")
    ) {
      return "success";
    } else {
      return "default";
    }
  }
}
