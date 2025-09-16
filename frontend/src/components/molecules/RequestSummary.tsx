import React from "react";
import { Box, Typography } from "@mui/material";
import { RequestStatusChip } from "../atoms";
import { type DetailedRequestResponse } from "../../types";

export interface RequestSummaryProps {
  request: DetailedRequestResponse;
  showTitle?: boolean;
  variant?: "default" | "compact";
}

export const RequestSummary: React.FC<RequestSummaryProps> = ({
  request,
  showTitle = true,
  variant = "default",
}) => {
  const containerSx =
    variant === "compact"
      ? { mb: 2, p: 1.5, bgcolor: "grey.50", borderRadius: 1 }
      : { mb: 3, p: 2, bgcolor: "grey.50", borderRadius: 1 };

  return (
    <Box sx={containerSx}>
      {showTitle && (
        <Typography variant="h6" gutterBottom>
          Request Summary
        </Typography>
      )}
      <Box display="grid" gridTemplateColumns="repeat(3, 1fr)" gap={2}>
        <Box>
          <Typography variant="caption" color="textSecondary">
            Application
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: "medium" }}>
            {request.request.application_name} v{request.request.version}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="textSecondary">
            Requestor
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: "medium" }}>
            {request.request.requestor.full_name} (@
            {request.request.requestor.username})
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="textSecondary">
            Status
          </Typography>
          <Box sx={{ mt: 0.5 }}>
            <RequestStatusChip status={request.request.status} size="small" />
          </Box>
        </Box>
        <Box>
          <Typography variant="caption" color="textSecondary">
            Created
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: "medium" }}>
            {new Date(request.request.created_at).toLocaleString()}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="textSecondary">
            Progress
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: "medium" }}>
            {Math.round(
              (request.request.completion_percentage / 100) *
                request.request.total_packages
            )}{" "}
            of {request.request.total_packages} packages processed
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};

export default RequestSummary;
