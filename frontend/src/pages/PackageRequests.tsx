import React, { useMemo } from "react";
import { useQuery } from "react-query";
import { Box, Typography, CircularProgress, Alert, Chip } from "@mui/material";
import { MaterialReactTable, type MRT_ColumnDef } from "material-react-table";
import { api, endpoints } from "../services/api";

interface Package {
  id: number;
  name: string;
  version: string;
  status: string;
  security_score: number | null;
  validation_errors: string[];
  type?: "new" | "existing";
}

interface PackageRequest {
  id: number;
  status: string;
  total_packages: number;
  validated_packages: number;
  created_at: string;
  application: {
    name: string;
    version: string;
  };
  packages: Package[];
}

export default function PackageRequests() {
  const {
    data: requests,
    isLoading,
    error,
  } = useQuery<PackageRequest[]>("packageRequests", async () => {
    const response = await api.get(endpoints.packages.requests);
    return response.data.requests;
  });

  // Transform data for the table
  const tableData = useMemo(() => {
    if (!requests) return [];

    return requests.flatMap(
      (request) =>
        request.packages?.map((pkg) => ({
          id: `${request.id}-${pkg.id}`,
          requestId: request.id,
          applicationName: request.application.name,
          applicationVersion: request.application.version,
          packageName: pkg.name,
          packageVersion: pkg.version,
          status: pkg.status,
          securityScore: pkg.security_score,
          validationErrors: pkg.validation_errors || [],
          type: pkg.type,
          createdAt: request.created_at,
          updatedAt: request.updated_at,
          requestorName:
            request.requestor?.full_name ||
            request.requestor?.username ||
            "Unknown",
          progress: `${request.validated_packages}/${request.total_packages}`,
          requestStatus: request.status,
        })) || []
    );
  }, [requests]);

  // Define columns for package rows only
  const columns = useMemo<MRT_ColumnDef<any>[]>(
    () => [
      {
        accessorKey: "requestId",
        header: "Request ID",
        size: 100,
        enableHiding: true,
      },
      {
        accessorKey: "packageName",
        header: "Package",
        size: 200,
        Cell: ({ row }) => (
          <Box display="flex" alignItems="center" gap={1}>
            {row.original.packageName}
            {row.original.type === "existing" && (
              <Chip
                label="Already Validated"
                size="small"
                color="success"
                variant="outlined"
              />
            )}
          </Box>
        ),
      },
      {
        accessorKey: "packageVersion",
        header: "Package Version",
        size: 120,
      },
      {
        accessorKey: "status",
        header: "Status",
        size: 120,
        Cell: ({ row }) => (
          <Chip
            label={row.original.status}
            color={getStatusColor(row.original.status)}
            size="small"
          />
        ),
      },
      {
        accessorKey: "securityScore",
        header: "Security Score",
        size: 120,
        Cell: ({ row }) =>
          row.original.securityScore !== null ? (
            <Chip
              label={`${row.original.securityScore}/100`}
              color={getScoreColor(row.original.securityScore)}
              size="small"
            />
          ) : (
            "N/A"
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
          enableRowVirtualization
          enableGrouping={false}
          enableExpanding
          getRowCanExpand={(row) => row.depth === 0}
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
            pagination: { pageSize: 25, pageIndex: 0 },
            grouping: ["requestId"],
            expanded: true,
            columnVisibility: { requestId: false },
          }}
          displayColumnDefOptions={{
            "mrt-row-expand": {
              size: 40,
            },
          }}
          renderGroupRow={({ row }) => {
            const firstRow = row.subRows?.[0];
            if (firstRow) {
              return (
                <Box sx={{ p: 2, width: "100%" }}>
                  <Typography
                    variant="h6"
                    gutterBottom
                    sx={{ fontWeight: "bold" }}
                  >
                    Request #{firstRow.original.requestId}
                  </Typography>

                  {/* Summary Table */}
                  <Box
                    sx={{
                      display: "grid",
                      gridTemplateColumns: "repeat(5, 1fr)",
                      gap: 2,
                      mt: 1,
                      p: 2,
                      bgcolor: "grey.50",
                      borderRadius: 1,
                      border: "1px solid",
                      borderColor: "grey.300",
                    }}
                  >
                    <Box>
                      <Typography
                        variant="caption"
                        color="textSecondary"
                        display="block"
                      >
                        Application
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                        {firstRow.original.applicationName}
                      </Typography>
                    </Box>

                    <Box>
                      <Typography
                        variant="caption"
                        color="textSecondary"
                        display="block"
                      >
                        Version
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                        {firstRow.original.applicationVersion}
                      </Typography>
                    </Box>

                    <Box>
                      <Typography
                        variant="caption"
                        color="textSecondary"
                        display="block"
                      >
                        Created
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                        {new Date(
                          firstRow.original.createdAt
                        ).toLocaleDateString()}
                      </Typography>
                    </Box>

                    <Box>
                      <Typography
                        variant="caption"
                        color="textSecondary"
                        display="block"
                      >
                        Requestor
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                        {firstRow.original.requestorName}
                      </Typography>
                    </Box>

                    <Box>
                      <Typography
                        variant="caption"
                        color="textSecondary"
                        display="block"
                      >
                        Progress
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: "medium" }}>
                        {firstRow.original.progress}
                      </Typography>
                    </Box>
                  </Box>
                </Box>
              );
            }
            return null;
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
    </Box>
  );
}

function getStatusColor(
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
    case "validating":
      return "warning";
    case "validated":
      return "success";
    case "already_validated":
      return "success";
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
