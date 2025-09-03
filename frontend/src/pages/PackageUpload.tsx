import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import {
  Box,
  Typography,
  Paper,
  Button,
  Alert,
  CircularProgress,
  Card,
  CardContent,
} from "@mui/material";
import { CloudUpload, Description } from "@mui/icons-material";
import { api, endpoints } from "../services/api";

export default function PackageUpload() {
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [error, setError] = useState("");

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    if (!file.name.endsWith(".json")) {
      setError("Please upload a JSON file (package-lock.json)");
      return;
    }

    setUploading(true);
    setError("");
    setUploadResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await api.post(endpoints.packages.upload, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setUploadResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.error || "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/json": [".json"],
    },
    multiple: false,
  });

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Upload Package Lock File
      </Typography>

      <Typography variant="body1" color="textSecondary" paragraph>
        Upload your package-lock.json file to start the package validation
        process.
      </Typography>

      <Paper
        {...getRootProps()}
        sx={{
          p: 4,
          textAlign: "center",
          cursor: "pointer",
          border: "2px dashed",
          borderColor: isDragActive ? "primary.main" : "grey.300",
          backgroundColor: isDragActive ? "primary.50" : "grey.50",
          "&:hover": {
            borderColor: "primary.main",
            backgroundColor: "primary.50",
          },
        }}
      >
        <input {...getInputProps()} />

        <CloudUpload sx={{ fontSize: 48, color: "primary.main", mb: 2 }} />

        <Typography variant="h6" gutterBottom>
          {isDragActive
            ? "Drop the file here"
            : "Drag & drop package-lock.json here"}
        </Typography>

        <Typography variant="body2" color="textSecondary" paragraph>
          or click to select a file
        </Typography>

        <Button variant="outlined" component="span">
          Select File
        </Button>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}

      {uploading && (
        <Box display="flex" alignItems="center" justifyContent="center" mt={2}>
          <CircularProgress size={20} sx={{ mr: 1 }} />
          <Typography>Uploading and processing package...</Typography>
        </Box>
      )}

      {uploadResult && (
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Typography variant="h6" color="success.main" gutterBottom>
              Upload Successful!
            </Typography>

            <Typography variant="body2" paragraph>
              <strong>Request ID:</strong> {uploadResult.request_id}
            </Typography>

            <Typography variant="body2" paragraph>
              <strong>Application:</strong> {uploadResult.application.name} v
              {uploadResult.application.version}
            </Typography>

            <Typography variant="body2" color="textSecondary">
              Your package-lock.json file has been uploaded and is being
              processed. You can track the progress in the Package Requests
              section.
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
