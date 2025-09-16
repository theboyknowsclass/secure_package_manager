import React, { useMemo, useState } from "react";
import { Box, Typography, Alert, IconButton } from "@mui/material";
import { MaterialReactTable, type MRT_ColumnDef } from "material-react-table";
import { Visibility, Download } from "@mui/icons-material";
import { usePackageRequests } from "../services/api/packageService";
import { type PackageRequest, type DetailedRequestResponse } from "../types";
import { LoadingSpinner, PackageStatusChip } from "../components/atoms";
import RequestDetailDialog from "../components/RequestDetailDialog";

export default function RequestStatus() {
  const [selectedRequest, setSelectedRequest] =
    useState<DetailedRequestResponse | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selectedRequestId, setSelectedRequestId] = useState<number | null>(
    null
  );

  const {
    data: requests,
    isLoading,
    error,
  } = usePackageRequests({ refetchInterval: 5000 });

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

    return requests.map((request: PackageRequest) => ({
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
      validatedPackages: Math.round(
        (request.completion_percentage / 100) * request.total_packages
      ),
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
          <PackageStatusChip
            status={row.original.status}
            size="small"
            showTooltip={true}
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
              <Typography
                variant="body2"
                sx={{ fontWeight: "medium", color: progressColor }}
              >
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
    return <LoadingSpinner message="Loading package requests..." />;
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
