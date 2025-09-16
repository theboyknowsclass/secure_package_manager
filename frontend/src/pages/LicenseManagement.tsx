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
  TextField,
  IconButton,
  Tooltip,
  ToggleButton,
  ToggleButtonGroup,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";
import { MaterialReactTable, type MRT_ColumnDef } from "material-react-table";
import {
  Add,
  Edit,
  Delete,
  CheckCircle,
  Warning,
  Info,
  Error,
} from "@mui/icons-material";
import { api, endpoints } from "../services/api";
import { CreateLicenseData, UpdateLicenseData } from "../types/license";

interface SupportedLicense {
  id: number;
  name: string;
  identifier: string;
  status: "always_allowed" | "allowed" | "avoid" | "blocked";
  created_by: number;
  created_at: string;
  updated_at: string;
}

// Helper function to get status icon and color
const getStatusDisplay = (status: string) => {
  switch (status) {
    case "always_allowed":
      return {
        icon: <CheckCircle />,
        color: "success",
        label: "Always Allowed",
      };
    case "allowed":
      return { icon: <Info />, color: "info", label: "Allowed" };
    case "avoid":
      return { icon: <Warning />, color: "warning", label: "Avoid" };
    case "blocked":
      return { icon: <Error />, color: "error", label: "Blocked" };
    default:
      return { icon: <Info />, color: "default", label: status };
  }
};

export default function LicenseManagement() {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [selectedLicenses, setSelectedLicenses] = useState<SupportedLicense[]>(
    []
  );
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [rowSelection, setRowSelection] = useState({});
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingLicense, setEditingLicense] = useState<SupportedLicense | null>(
    null
  );
  const [currentView, setCurrentView] = useState<
    "all" | "always_allowed" | "allowed" | "avoid" | "blocked"
  >("all");
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: "",
    severity: "success" as "success" | "error" | "warning" | "info",
  });

  // Form state
  const [formData, setFormData] = useState({
    name: "",
    identifier: "",
    status: "allowed" as "always_allowed" | "allowed" | "avoid" | "blocked",
  });

  const queryClient = useQueryClient();

  const {
    data: licenses,
    isLoading,
    error,
  } = useQuery<SupportedLicense[]>(
    ["supportedLicenses", currentView],
    async () => {
      const response = await api.get(
        endpoints.admin.licenses(
          currentView === "all" ? undefined : currentView
        )
      );
      return response.data.licenses;
    }
  );

  const createMutation = useMutation(
    async (licenseData: CreateLicenseData) => {
      const response = await api.post(endpoints.admin.licenses(), licenseData);
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(["supportedLicenses"]);
        setSnackbar({
          open: true,
          message: "License created successfully!",
          severity: "success",
        });
        setCreateDialogOpen(false);
        resetForm();
      },
      onError: (error: unknown) => {
        const errorData = (
          error as { response?: { data?: { error?: string } } }
        )?.response?.data;
        setSnackbar({
          open: true,
          message: errorData?.error || "Failed to create license",
          severity: "error",
        });
      },
    }
  );

  const updateMutation = useMutation(
    async ({ id, data }: { id: number; data: UpdateLicenseData }) => {
      const response = await api.put(endpoints.admin.license(id), data);
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(["supportedLicenses"]);
        setSnackbar({
          open: true,
          message: "License updated successfully!",
          severity: "success",
        });
        setEditDialogOpen(false);
        setEditingLicense(null);
        resetForm();
      },
      onError: (error: unknown) => {
        const errorData = (
          error as { response?: { data?: { error?: string } } }
        )?.response?.data;
        setSnackbar({
          open: true,
          message: errorData?.error || "Failed to update license",
          severity: "error",
        });
      },
    }
  );

  const deleteMutation = useMutation(
    async (id: number) => {
      const response = await api.delete(endpoints.admin.license(id));
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(["supportedLicenses"]);
        setSnackbar({
          open: true,
          message: "License deleted successfully!",
          severity: "success",
        });
        setDeleteDialogOpen(false);
        setEditingLicense(null);
      },
      onError: (error: unknown) => {
        const errorData = (
          error as { response?: { data?: { error?: string } } }
        )?.response?.data;
        setSnackbar({
          open: true,
          message: errorData?.error || "Failed to delete license",
          severity: "error",
        });
      },
    }
  );

  // Define columns - moved before conditional returns to fix hooks order
  const columns = useMemo<MRT_ColumnDef<SupportedLicense>[]>(
    () => [
      {
        accessorKey: "identifier",
        header: "SPDX Identifier",
        size: 150,
      },
      {
        accessorKey: "name",
        header: "License Name",
        size: 300,
        Cell: ({ row }) => (
          <Typography
            variant="body2"
            sx={{
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              maxWidth: "100%",
            }}
          >
            {row.original.name}
          </Typography>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        size: 150,
        Cell: ({ row }) => {
          const statusDisplay = getStatusDisplay(row.original.status);
          return (
            <Chip
              icon={statusDisplay.icon}
              label={statusDisplay.label}
              color={
                statusDisplay.color as
                  | "default"
                  | "primary"
                  | "secondary"
                  | "error"
                  | "info"
                  | "success"
                  | "warning"
              }
              size="small"
            />
          );
        },
      },
      {
        id: "actions",
        header: "Actions",
        size: 120,
        Cell: ({ row }) => (
          <Box sx={{ display: "flex", gap: 1 }}>
            <Tooltip title="Edit License">
              <IconButton
                size="small"
                onClick={() => handleEditLicense(row.original)}
              >
                <Edit />
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete License">
              <IconButton
                size="small"
                color="error"
                onClick={() => handleDeleteLicense(row.original)}
              >
                <Delete />
              </IconButton>
            </Tooltip>
          </Box>
        ),
      },
    ],
    []
  );

  const resetForm = () => {
    setFormData({
      name: "",
      identifier: "",
      status: "allowed",
    });
  };

  const handleCreateLicense = () => {
    setCreateDialogOpen(true);
    resetForm();
  };

  const handleEditLicense = (license: SupportedLicense) => {
    setEditingLicense(license);
    setFormData({
      name: license.name,
      identifier: license.identifier,
      status: license.status,
    });
    setEditDialogOpen(true);
  };

  const handleDeleteLicense = (license: SupportedLicense) => {
    setEditingLicense(license);
    setDeleteDialogOpen(true);
  };

  const handleSubmitCreate = () => {
    createMutation.mutate(formData);
  };

  const handleSubmitEdit = () => {
    if (editingLicense) {
      updateMutation.mutate({ id: editingLicense.id, data: formData });
    }
  };

  const handleConfirmDelete = () => {
    if (editingLicense) {
      deleteMutation.mutate(editingLicense.id);
    }
  };

  const handleFormChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

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
        Failed to load supported licenses. Please try again.
      </Alert>
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Settings
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Manage license policies and system settings.
        </Typography>
      </Box>

      <Box>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 3,
          }}
        >
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={handleCreateLicense}
          >
            Add License
          </Button>
        </Box>

        {/* View Toggle */}
        <Box sx={{ mb: 3 }}>
          <ToggleButtonGroup
            value={currentView}
            exclusive
            onChange={(_, newView) => newView && setCurrentView(newView)}
            aria-label="license list view"
          >
            <ToggleButton value="all" aria-label="all licenses">
              All Licenses
            </ToggleButton>
            <ToggleButton value="always_allowed" aria-label="always allowed">
              <CheckCircle sx={{ mr: 1 }} />
              Always Allowed
            </ToggleButton>
            <ToggleButton value="allowed" aria-label="allowed">
              <Info sx={{ mr: 1 }} />
              Allowed
            </ToggleButton>
            <ToggleButton value="avoid" aria-label="avoid">
              <Warning sx={{ mr: 1 }} />
              Avoid
            </ToggleButton>
            <ToggleButton value="blocked" aria-label="blocked">
              <Error sx={{ mr: 1 }} />
              Blocked
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>

        {licenses && licenses.length > 0 ? (
          <MaterialReactTable
            columns={columns}
            data={licenses}
            enableColumnFilters
            enableGlobalFilter
            enableSorting
            enableColumnResizing
            enablePagination={false}
            muiTableProps={{
              sx: {
                tableLayout: "fixed",
                width: "100%",
              },
            }}
            muiTableContainerProps={{
              sx: {
                maxHeight: "70vh",
              },
            }}
            initialState={{
              density: "compact",
              columnSizing: {
                identifier: 150,
                name: 300,
                status: 150,
                actions: 120,
              },
            }}
          />
        ) : (
          <Box sx={{ p: 3, textAlign: "center" }}>
            <Typography variant="h6" color="textSecondary">
              No licenses found
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Add your first supported license to get started.
            </Typography>
          </Box>
        )}

        {/* Create License Dialog */}
        <Dialog
          open={createDialogOpen}
          onClose={() => setCreateDialogOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle>Add New License</DialogTitle>
          <DialogContent>
            <Box
              sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}
            >
              <TextField
                label="License Name"
                value={formData.name}
                onChange={e => handleFormChange("name", e.target.value)}
                fullWidth
                required
              />
              <TextField
                label="SPDX Identifier"
                value={formData.identifier}
                onChange={e => handleFormChange("identifier", e.target.value)}
                fullWidth
                required
                helperText="e.g., MIT, Apache-2.0, GPL-3.0"
              />
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Select
                  value={formData.status}
                  label="Status"
                  onChange={e => handleFormChange("status", e.target.value)}
                >
                  <MenuItem value="always_allowed">
                    <CheckCircle sx={{ mr: 1 }} />
                    Always Allowed
                  </MenuItem>
                  <MenuItem value="allowed">
                    <Info sx={{ mr: 1 }} />
                    Allowed
                  </MenuItem>
                  <MenuItem value="avoid">
                    <Warning sx={{ mr: 1 }} />
                    Avoid
                  </MenuItem>
                  <MenuItem value="blocked">
                    <Error sx={{ mr: 1 }} />
                    Blocked
                  </MenuItem>
                </Select>
              </FormControl>
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={handleSubmitCreate}
              variant="contained"
              disabled={
                createMutation.isLoading ||
                !formData.name ||
                !formData.identifier
              }
            >
              {createMutation.isLoading ? "Creating..." : "Create License"}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Edit License Dialog */}
        <Dialog
          open={editDialogOpen}
          onClose={() => setEditDialogOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle>Edit License</DialogTitle>
          <DialogContent>
            <Box
              sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}
            >
              <TextField
                label="License Name"
                value={formData.name}
                onChange={e => handleFormChange("name", e.target.value)}
                fullWidth
                required
              />
              <TextField
                label="SPDX Identifier"
                value={formData.identifier}
                onChange={e => handleFormChange("identifier", e.target.value)}
                fullWidth
                required
                disabled
                helperText="SPDX identifier cannot be changed"
              />
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Select
                  value={formData.status}
                  label="Status"
                  onChange={e => handleFormChange("status", e.target.value)}
                >
                  <MenuItem value="always_allowed">
                    <CheckCircle sx={{ mr: 1 }} />
                    Always Allowed
                  </MenuItem>
                  <MenuItem value="allowed">
                    <Info sx={{ mr: 1 }} />
                    Allowed
                  </MenuItem>
                  <MenuItem value="avoid">
                    <Warning sx={{ mr: 1 }} />
                    Avoid
                  </MenuItem>
                  <MenuItem value="blocked">
                    <Error sx={{ mr: 1 }} />
                    Blocked
                  </MenuItem>
                </Select>
              </FormControl>
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={handleSubmitEdit}
              variant="contained"
              disabled={updateMutation.isLoading || !formData.name}
            >
              {updateMutation.isLoading ? "Updating..." : "Update License"}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog
          open={deleteDialogOpen}
          onClose={() => setDeleteDialogOpen(false)}
        >
          <DialogTitle>Delete License</DialogTitle>
          <DialogContent>
            <Typography>
              Are you sure you want to delete the license{" "}
              <strong>{editingLicense?.name}</strong>?
            </Typography>
            <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
              This action cannot be undone. Make sure no packages are using this
              license.
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={handleConfirmDelete}
              variant="contained"
              color="error"
              disabled={deleteMutation.isLoading}
            >
              {deleteMutation.isLoading ? "Deleting..." : "Delete"}
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
    </Box>
  );
}
