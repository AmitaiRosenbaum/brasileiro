import {
  Avatar,
  Button,
  Divider,
  Paper,
  Popover,
  Stack,
  Typography,
} from "@mui/material";
import type React from "react";
import type { AuthenticatedUser } from "../api/auth";
import { navigateTo } from "../utils/navigation";

type ProfileMenuProps = {
  currentUser: AuthenticatedUser | null;
  onLogout: () => void;
  anchorEl: HTMLElement | null;
  onClose: () => void;
};

function getInitials(user: AuthenticatedUser | null) {
  if (!user) {
    return "?";
  }

  const source = `${user.first_name} ${user.last_name}`.trim() || user.username;
  return source
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export function ProfileAvatarButton({
  currentUser,
  onClick,
}: {
  currentUser: AuthenticatedUser | null;
  onClick: (event: React.MouseEvent<HTMLButtonElement>) => void;
}) {
  return (
    <Button
      onClick={onClick}
      sx={{
        minWidth: 0,
        p: 0,
        borderRadius: 999,
      }}
    >
      <Avatar
        sx={{
          width: 38,
          height: 38,
          bgcolor: "#14532d",
          color: "#fffaf3",
          fontWeight: 800,
          boxShadow: "0 10px 30px rgba(28, 25, 23, 0.12)",
        }}
      >
        {getInitials(currentUser)}
      </Avatar>
    </Button>
  );
}

export default function ProfileMenu({
  currentUser,
  onLogout,
  anchorEl,
  onClose,
}: ProfileMenuProps) {
  const handleSettingsClick = () => {
    onClose();
    navigateTo("/settings");
  };

  const displayName =
    `${currentUser?.first_name ?? ""} ${currentUser?.last_name ?? ""}`.trim() ||
    currentUser?.username ||
    "Unknown user";

  return (
    <Popover
      open={Boolean(anchorEl)}
      anchorEl={anchorEl}
      onClose={onClose}
      anchorOrigin={{
        vertical: "bottom",
        horizontal: "right",
      }}
      transformOrigin={{
        vertical: "top",
        horizontal: "right",
      }}
      slotProps={{
        paper: {
          sx: {
            mt: 1.25,
            borderRadius: 3,
            overflow: "hidden",
            boxShadow: "0 24px 80px rgba(28, 25, 23, 0.18)",
          },
        },
      }}
    >
      <Paper elevation={0} sx={{ p: 2.25, minWidth: 300 }}>
        <Stack spacing={2}>
          <Stack direction="row" spacing={2} alignItems="center">
            <Avatar
              sx={{
                width: 52,
                height: 52,
                bgcolor: "#14532d",
                color: "#fffaf3",
                fontWeight: 800,
              }}
            >
              {getInitials(currentUser)}
            </Avatar>
            <Stack spacing={0.25}>
              <Typography sx={{ fontWeight: 800 }}>{displayName}</Typography>
              <Typography color="text.secondary">@{currentUser?.username}</Typography>
              {currentUser?.email ? (
                <Typography color="text.secondary">{currentUser.email}</Typography>
              ) : null}
            </Stack>
          </Stack>

          <Divider />

          <Stack direction="row" justifyContent="flex-end" spacing={1.25}>
            <Button onClick={handleSettingsClick} sx={{ color: "#14532d", fontWeight: 700 }}>
              Settings
            </Button>
            <Button
              variant="outlined"
              onClick={onLogout}
              sx={{
                borderColor: "rgba(20, 83, 45, 0.28)",
                color: "#14532d",
                fontWeight: 700,
                borderRadius: 999,
              }}
            >
              Log out
            </Button>
          </Stack>
        </Stack>
      </Paper>
    </Popover>
  );
}
