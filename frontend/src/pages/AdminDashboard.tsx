import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "react-query";
import {
  Box,
  Typography,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
} from "@mui/material";
import { MaterialReactTable, type MRT_ColumnDef } from "material-react-table";
import { CheckCircle, Warning } from "@mui/icons-material";
import { api, endpoints } from "../services/api";

interface ValidatedPackage {
  id: number;
  name: string;
  version: string;
  security_score: number;
  license_score: number;
  license_identifier: string;
  validation_errors: string[];
  request: {
    id: number;
    application: {
      name: string;
      version: string;
    };
  };
}

export default function AdminDashboard() {
  const [selectedPackages, setSelectedPackages] = useState<ValidatedPackage[]>(
    []
  );
  const [rowSelection, setRowSelection] = useState({});
  const [approveDialogOpen, setApproveDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: "",
    severity: "success" as any,
  });

  const queryClient = useQueryClient();

  const {
    data: packages,
    isLoading,
    error,
  } = useQuery<ValidatedPackage[]>("validatedPackages", async () => {
    const response = await api.get(endpoints.admin.validatedPackages);
    return response.data.packages || [];
  }, {
    retry: 1,
    retryDelay: 1000,
    staleTime: 30000, // 30 seconds
  });

  const approveMutation = useMutation(
    async (packageIds: number[]) => {
      // Approve multiple packages
      await Promise.all(
        packageIds.map((id) => api.post(endpoints.admin.approvePackage(id)))
      );
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries("validatedPackages");
        setSnackbar({
          open: true,
          message: `${selectedPackages.length} package(s) approved successfully! Publishing will happen automatically.`,
          severity: "success",
        });
        setApproveDialogOpen(false);
        setSelectedPackages([]);
      },
      onError: () => {
        setSnackbar({
          open: true,
          message: "Failed to approve packages",
          severity: "error",
        });
      },
    }
  );

  // Define columns - moved before conditional returns to fix hooks order
  const columns = useMemo<MRT_ColumnDef<ValidatedPackage>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Package",
        size: 200,
      },
      {
        accessorKey: "version",
        header: "Version",
        size: 120,
      },
      {
        accessorKey: "request.application.name",
        header: "Application",
        size: 200,
        Cell: ({ row }) =>
          `${row.original.request.application.name} v${row.original.request.application.version}`,
      },
      {
        accessorKey: "security_score",
        header: "Security Score",
        size: 140,
        Cell: ({ row }) => (
          <Chip
            label={`${row.original.security_score}/100`}
            color={getScoreColor(row.original.security_score)}
            size="small"
          />
        ),
      },
      {
        accessorKey: "license_score",
        header: "License Score",
        size: 140,
        Cell: ({ row }) => (
          <Chip
            label={`${row.original.license_score}/100`}
            color={getScoreColor(row.original.license_score)}
            size="small"
          />
        ),
      },
      {
        accessorKey: "license_identifier",
        header: "License",
        size: 120,
        Cell: ({ row }) => (
          <Chip
            label={row.original.license_identifier || "Unknown"}
            color={row.original.license_score >= 80 ? "success" : row.original.license_score >= 60 ? "warning" : "error"}
            size="small"
          />
        ),
      },
      {
        accessorKey: "validation_errors",
        header: "Validation Errors",
        size: 150,
        Cell: ({ row }) =>
          row.original.validation_errors &&
          row.original.validation_errors.length > 0 ? (
            <Chip
              icon={<Warning />}
              label={`${row.original.validation_errors.length} errors`}
              color="warning"
              size="small"
            />
          ) : (
            <Chip label="No errors" color="success" size="small" />
          ),
      },
    ],
    []
  );

  const handleBulkApprove = () => {
    if (selectedPackages.length > 0) {
      setApproveDialogOpen(true);
    }
  };

  const confirmBulkApprove = () => {
    const packageIds = selectedPackages.map((pkg) => pkg.id);
    approveMutation.mutate(packageIds);
  };

  // Handle row selection changes
  const handleRowSelectionChange = (updaterOrValue: any) => {
    setRowSelection(updaterOrValue);

    // Convert row selection to selected packages
    if (packages) {
      const selectedRows = Object.keys(updaterOrValue).filter(
        (key) => updaterOrValue[key]
      );
      const selected = selectedRows.map((index) => packages[parseInt(index)]);
      setSelectedPackages(selected);
    }
  };

  if (isLoading) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom>
          Approve Packages
        </Typography>
        <Typography variant="body1" color="textSecondary" paragraph>
          Review validated packages and manage the approval and publishing workflow.
        </Typography>
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          minHeight="50vh"
        >
          <CircularProgress />
        </Box>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        Failed to load validated packages. Please try again.
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Approve Packages
      </Typography>

      <Typography variant="body1" color="textSecondary" paragraph>
        Review validated packages and manage the approval and publishing
        workflow.
      </Typography>

      {packages && packages.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Button
            variant="contained"
            startIcon={<CheckCircle />}
            onClick={handleBulkApprove}
            disabled={
              selectedPackages.length === 0 || approveMutation.isLoading
            }
            sx={{ mb: 2 }}
          >
            Approve Selected ({selectedPackages.length})
          </Button>
        </Box>
      )}

      {packages && packages.length > 0 ? (
        <MaterialReactTable
          columns={columns}
          data={packages}
          enableColumnFilters
          enableGlobalFilter
          enableRowSelection
          enableSorting
          enableColumnResizing
          enableRowVirtualization
          onRowSelectionChange={handleRowSelectionChange}
          state={{ rowSelection }}
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
          }}
        />
      ) : (
        <Box sx={{ p: 3, textAlign: "center" }}>
          <Typography variant="h6" color="textSecondary">
            No validated packages found
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Packages will appear here after they have been validated and are
            ready for review.
          </Typography>
        </Box>
      )}

      {/* Bulk Approve Dialog */}
      <Dialog
        open={approveDialogOpen}
        onClose={() => setApproveDialogOpen(false)}
      >
        <DialogTitle>Approve Packages</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to approve{" "}
            <strong>{selectedPackages.length} package(s)</strong>?
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
            Selected packages will be approved and automatically published to
            the secure repository.
          </Typography>
          {selectedPackages.length > 0 && (
            <Box sx={{ mt: 2, maxHeight: 200, overflow: "auto" }}>
              <Typography variant="subtitle2" gutterBottom>
                Packages to be approved:
              </Typography>
              {selectedPackages.map((pkg) => (
                <Typography key={pkg.id} variant="body2" sx={{ ml: 2 }}>
                  • {pkg.name}@{pkg.version}
                </Typography>
              ))}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApproveDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={confirmBulkApprove}
            variant="contained"
            disabled={approveMutation.isLoading}
          >
            {approveMutation.isLoading ? "Approving..." : "Approve All"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert
          severity={snackbar.severity}
          onClose={() => setSnackbar({ ...snackbar, open: false })}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
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
