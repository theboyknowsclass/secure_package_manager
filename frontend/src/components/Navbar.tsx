import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
  Menu,
  MenuItem,
} from "@mui/material";
import { AccountCircle } from "@mui/icons-material";
import { useAuth } from "../hooks/useAuth";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
    handleClose();
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Secure Package Manager
        </Typography>

        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Button
            color="inherit"
            onClick={() => navigate("/")}
            sx={{
              backgroundColor: isActive("/")
                ? "rgba(255, 255, 255, 0.1)"
                : "transparent",
            }}
          >
            Dashboard
          </Button>

          <Button
            color="inherit"
            onClick={() => navigate("/request")}
            sx={{
              backgroundColor: isActive("/request")
                ? "rgba(255, 255, 255, 0.1)"
                : "transparent",
            }}
          >
            Request
          </Button>

          <Button
            color="inherit"
            onClick={() => navigate("/status")}
            sx={{
              backgroundColor: isActive("/status")
                ? "rgba(255, 255, 255, 0.1)"
                : "transparent",
            }}
          >
            Status
          </Button>

          {/* Approve section - for approvers and admins */}
          {(user?.role === "approver" || user?.role === "admin") && (
            <Button
              color="inherit"
              onClick={() => navigate("/approve")}
              sx={{
                backgroundColor: isActive("/approve")
                  ? "rgba(255, 255, 255, 0.1)"
                  : "transparent",
              }}
            >
              Approve
            </Button>
          )}

          {/* Settings section - for admins only */}
          {user?.role === "admin" && (
            <Button
              color="inherit"
              onClick={() => navigate("/settings")}
              sx={{
                backgroundColor: isActive("/settings")
                  ? "rgba(255, 255, 255, 0.1)"
                  : "transparent",
              }}
            >
              Settings
            </Button>
          )}

          <IconButton
            size="large"
            aria-label="account of current user"
            aria-controls="menu-appbar"
            aria-haspopup="true"
            onClick={handleMenu}
            color="inherit"
          >
            <AccountCircle />
          </IconButton>

          <Menu
            id="menu-appbar"
            anchorEl={anchorEl}
            anchorOrigin={{
              vertical: "top",
              horizontal: "right",
            }}
            keepMounted
            transformOrigin={{
              vertical: "top",
              horizontal: "right",
            }}
            open={Boolean(anchorEl)}
            onClose={handleClose}
          >
            <MenuItem disabled>
              <Typography variant="body2">
                {user?.full_name} ({user?.role})
              </Typography>
            </MenuItem>
            <MenuItem onClick={handleLogout}>Logout</MenuItem>
          </Menu>
        </Box>
      </Toolbar>
    </AppBar>
  );
}
