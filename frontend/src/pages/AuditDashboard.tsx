import React, { useMemo } from "react";
import { Box, Typography, Chip, Alert, CircularProgress } from "@mui/material";
import { MaterialReactTable, type MRT_ColumnDef } from "material-react-table";
import { useAuditData } from "../services/api/packageService";
import { AuditDataItem } from "../types/package";

export default function AuditDashboard() {
  const { data: auditData, isLoading, error } = useAuditData();

  // Memoized cell components to prevent re-renders
  const PackageNameCell = React.memo(({ value }: { value: string }) => (
    <Typography variant="body2" sx={{ fontWeight: "medium" }}>
      {value}
    </Typography>
  ));

  const VersionCell = React.memo(({ value }: { value: string }) => (
    <Typography variant="body2">{value}</Typography>
  ));

  const LicenseCell = React.memo(({ value }: { value: string | null }) => {
    if (!value) {
      return (
        <Typography variant="body2" color="textSecondary">
          Unknown
        </Typography>
      );
    }

    return (
      <Chip label={value} color={getLicenseStatusColor(value)} size="small" />
    );
  });

  // Define columns for the audit table
  const columns = useMemo<MRT_ColumnDef<AuditDataItem>[]>(
    () => [
      {
        accessorKey: "package.name",
        header: "Package Name",
        size: 200,
        Cell: ({ row }) => (
          <PackageNameCell value={row.original.package.name} />
        ),
      },
      {
        accessorKey: "package.version",
        header: "Version",
        size: 120,
        Cell: ({ row }) => <VersionCell value={row.original.package.version} />,
      },
      {
        accessorKey: "package.license_identifier",
        header: "License",
        size: 150,
        Cell: ({ row }) => (
          <LicenseCell value={row.original.package.license_identifier} />
        ),
      },
      {
        accessorKey: "approval.approver",
        header: "Approved By",
        size: 150,
        Cell: ({ row }) => {
          const approver = row.original.approval.approver;
          if (!approver) {
            return (
              <Typography variant="body2" color="textSecondary">
                Unknown
              </Typography>
            );
          }

          return (
            <Box>
              <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                {approver.full_name}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                @{approver.username}
              </Typography>
            </Box>
          );
        },
      },
      {
        accessorKey: "approval.approved_at",
        header: "Approved At",
        size: 150,
        Cell: ({ row }) => {
          const approvedAt = row.original.approval.approved_at;
          if (!approvedAt) {
            return (
              <Typography variant="body2" color="textSecondary">
                Unknown
              </Typography>
            );
          }

          return (
            <Box>
              <Typography variant="body2">
                {new Date(approvedAt).toLocaleDateString()}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                {new Date(approvedAt).toLocaleTimeString()}
              </Typography>
            </Box>
          );
        },
      },
      {
        accessorKey: "original_request.application_name",
        header: "Original Application",
        size: 200,
        Cell: ({ row }) => {
          const originalRequest = row.original.original_request;
          if (!originalRequest) {
            return (
              <Typography variant="body2" color="textSecondary">
                Unknown
              </Typography>
            );
          }

          return (
            <Box>
              <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                {originalRequest.application_name}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                v{originalRequest.application_version}
              </Typography>
            </Box>
          );
        },
      },
      {
        accessorKey: "original_request.requestor",
        header: "Original Requestor",
        size: 150,
        Cell: ({ row }) => {
          const originalRequest = row.original.original_request;
          if (!originalRequest || !originalRequest.requestor) {
            return (
              <Typography variant="body2" color="textSecondary">
                Unknown
              </Typography>
            );
          }

          return (
            <Box>
              <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                {originalRequest.requestor.full_name}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                @{originalRequest.requestor.username}
              </Typography>
            </Box>
          );
        },
      },
      {
        accessorKey: "original_request.requested_at",
        header: "Requested At",
        size: 150,
        Cell: ({ row }) => {
          const originalRequest = row.original.original_request;
          if (!originalRequest || !originalRequest.requested_at) {
            return (
              <Typography variant="body2" color="textSecondary">
                Unknown
              </Typography>
            );
          }

          return (
            <Box>
              <Typography variant="body2">
                {new Date(originalRequest.requested_at).toLocaleDateString()}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                {new Date(originalRequest.requested_at).toLocaleTimeString()}
              </Typography>
            </Box>
          );
        },
      },
    ],
    [LicenseCell, PackageNameCell, VersionCell]
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
        Error loading audit data:{" "}
        {error instanceof Error ? error.message : "Unknown error"}
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Audit Dashboard
      </Typography>
      <Typography variant="body1" color="textSecondary" paragraph>
        View all approved packages with their approval history and original
        request information.
      </Typography>

      {auditData && auditData.length > 0 ? (
        <MaterialReactTable
          columns={columns}
          data={auditData}
          enableColumnFilters
          enableGlobalFilter
          enableSorting
          enableColumnResizing
          enablePagination
          enableRowVirtualization={auditData.length > 100}
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
            sorting: [{ id: "approval.approved_at", desc: true }], // Sort by newest approvals first
            pagination: {
              pageIndex: 0,
              pageSize: 25,
            },
          }}
        />
      ) : (
        <Box sx={{ p: 3, textAlign: "center" }}>
          <Typography variant="h6" color="textSecondary">
            No approved packages found
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Approved packages will appear here once they have been approved by
            an approver.
          </Typography>
        </Box>
      )}
    </Box>
  );
}

// Helper function for license status colors
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
