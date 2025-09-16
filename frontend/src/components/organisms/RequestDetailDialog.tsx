import React from "react";
import {
  Box,
  Typography,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from "@mui/material";
import { MaterialReactTable, type MRT_ColumnDef } from "material-react-table";
import { Close } from "@mui/icons-material";
import { usePackageRequest } from "../../services/api/packageService";
import { type Package } from "../../types/status";
import {
  PackageStatusChip,
  LicenseChip,
  SecurityScoreChip,
  LicenseScoreChip,
  VulnerabilityChip,
  PackageTypeChip,
  LoadingSpinner,
} from "../atoms";
import { RequestSummary } from "../molecules";
import { type SecurityScanStatus } from "../../types/securityStatus";

interface RequestDetailDialogProps {
  open: boolean;
  onClose: () => void;
  requestId: number | null;
  refetchInterval?: number;
}

// Define columns for package details table
const packageColumns: MRT_ColumnDef<Package>[] = [
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
    accessorKey: "status",
    header: "Status",
    size: 120,
    Cell: ({ row }) => <PackageStatusChip status={row.original.status} />,
  },
  {
    accessorKey: "license_identifier",
    header: "License",
    size: 120,
    Cell: ({ row }) => {
      const pkg = row.original;
      return (
        <LicenseChip
          identifier={pkg.license_identifier}
          score={pkg.license_score}
        />
      );
    },
  },
  {
    accessorKey: "license_score",
    header: "License Score",
    size: 120,
    Cell: ({ row }) => <LicenseScoreChip score={row.original.license_score} />,
  },
  {
    accessorKey: "security_score",
    header: "Security Score",
    size: 120,
    muiTableHeadCellProps: {
      sx: {
        "&:hover": {
          cursor: "default !important",
        },
      },
    },
    Cell: ({ row }) => {
      const pkg = row.original;
      return (
        <SecurityScoreChip
          score={pkg.security_score}
          scanStatus={pkg.security_scan_status as SecurityScanStatus}
          scanResult={pkg.scan_result}
        />
      );
    },
  },
  {
    accessorKey: "scan_result",
    header: "Vulnerabilities",
    size: 120,
    Cell: ({ row }) => {
      const pkg = row.original;
      return <VulnerabilityChip scanResult={pkg.scan_result} />;
    },
  },
  {
    accessorKey: "type",
    header: "Type",
    size: 80,
    Cell: ({ row }) => {
      const type = row.original.type;
      return (
        <PackageTypeChip type={type === "existing" ? "existing" : "new"} />
      );
    },
  },
];

export default function RequestDetailDialog({
  open,
  onClose,
  requestId,
  refetchInterval = 5000,
}: RequestDetailDialogProps) {
  const {
    data: selectedRequest,
    isLoading,
    error,
  } = usePackageRequest(requestId || 0, {
    refetchInterval: open ? refetchInterval : undefined,
  });

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
            <RequestSummary request={selectedRequest} />

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
              enableRowActions={false}
              enableRowSelection={false}
              muiTableProps={{
                sx: {
                  tableLayout: "fixed",
                  // Override cursor for tooltip columns to prevent interference
                  "& .MuiTableHead-root th[data-columnid='security_score']:hover":
                    {
                      cursor: "default !important",
                    },
                  "& .MuiTableHead-root th[data-columnid='license_score']:hover":
                    {
                      cursor: "default !important",
                    },
                  "& .MuiTableHead-root th[data-columnid='scan_result']:hover":
                    {
                      cursor: "default !important",
                    },
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
                  { id: "version", desc: false },
                ],
              }}
            />
          </Box>
        ) : isLoading ? (
          <LoadingSpinner
            message="Loading package details..."
            minHeight="200px"
          />
        ) : error ? (
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              minHeight: 200,
            }}
          >
            <Typography variant="body2" color="textSecondary">
              Failed to load request details. Please try again.
            </Typography>
          </Box>
        ) : (
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              minHeight: 200,
            }}
          >
            <Typography variant="body2" color="textSecondary">
              No request details available
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
