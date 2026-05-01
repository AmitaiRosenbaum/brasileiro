import {
  Alert,
  Box,
  Button,
  Container,
  Link,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import type React from "react";
import { useState } from "react";
import type { AuthenticatedUser } from "../api/auth";
import { updateCurrentUser } from "../api/auth";
import { deletePlaylist } from "../api/playlists";
import { navigateTo, navigateToPlaylist } from "../utils/navigation";

type SettingsPageProps = {
  currentUser: AuthenticatedUser | null;
  onCurrentUserChange: (user: AuthenticatedUser) => void;
  onLogout: () => void;
};

export default function SettingsPage({
  currentUser,
  onCurrentUserChange,
  onLogout,
}: SettingsPageProps) {
  const [email, setEmail] = useState(currentUser?.email ?? "");
  const [firstName, setFirstName] = useState(currentUser?.first_name ?? "");
  const [lastName, setLastName] = useState(currentUser?.last_name ?? "");
  const [isSaving, setIsSaving] = useState(false);
  const [deletingPlaylistId, setDeletingPlaylistId] = useState<number | null>(null);
  const [message, setMessage] = useState<{
    severity: "success" | "error";
    text: string;
  } | null>(null);

  const handleHomeClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    navigateTo("/");
  };

  const handleSubmit = async () => {
    setIsSaving(true);
    setMessage(null);

    try {
      const updatedUser = await updateCurrentUser({
        email: email.trim(),
        first_name: firstName.trim(),
        last_name: lastName.trim(),
      });
      onCurrentUserChange(updatedUser);
      setMessage({ severity: "success", text: "Settings saved." });
    } catch (_error) {
      setMessage({ severity: "error", text: "We couldn't save your settings right now." });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeletePlaylist = async (playlistId: number, playlistName: string) => {
    setDeletingPlaylistId(playlistId);
    setMessage(null);

    try {
      await deletePlaylist(playlistId);
      onCurrentUserChange({
        ...(currentUser as AuthenticatedUser),
        playlists: (currentUser?.playlists ?? []).filter((playlist) => playlist.id !== playlistId),
      });
      setMessage({ severity: "success", text: `${playlistName} was deleted.` });
    } catch (_error) {
      setMessage({ severity: "error", text: `We couldn't delete ${playlistName} right now.` });
    } finally {
      setDeletingPlaylistId(null);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background: "linear-gradient(145deg, #f7f3ed 0%, #eef4ee 46%, #f8efe7 100%)",
      }}
    >
      <Container maxWidth="md" sx={{ py: { xs: 3, md: 5 } }}>
        <Stack spacing={3}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            alignItems={{ xs: "flex-start", sm: "center" }}
            justifyContent="space-between"
            spacing={2}
          >
            <Stack spacing={1}>
              <Link color="inherit" underline="hover" href="/" onClick={handleHomeClick}>
                Brasileiro
              </Link>
              <Typography variant="h2">Settings</Typography>
            </Stack>
            <Stack direction="row" spacing={1.5} useFlexGap flexWrap="wrap">
              <Button
                variant="outlined"
                onClick={() => navigateTo("/")}
                sx={{
                  borderColor: "rgba(20, 83, 45, 0.28)",
                  color: "#14532d",
                  fontWeight: 700,
                  borderRadius: 999,
                }}
              >
                Back Home
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

          <Paper
            elevation={0}
            sx={{
              p: { xs: 3, sm: 4 },
              borderRadius: 2,
              border: "1px solid rgba(87, 83, 78, 0.14)",
              bgcolor: "rgba(255, 255, 255, 0.88)",
              boxShadow: "0 24px 80px rgba(28, 25, 23, 0.10)",
            }}
          >
            <Stack spacing={3}>
              <Box>
                <Typography variant="h5" sx={{ fontWeight: 800 }}>
                  Account
                </Typography>
                <Typography color="text.secondary">
                  Update the profile details already stored in the backend.
                </Typography>
              </Box>

              <TextField
                label="Username"
                value={currentUser?.username ?? ""}
                fullWidth
                disabled
              />
              <TextField
                label="Email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                fullWidth
                type="email"
              />
              <TextField
                label="First name"
                value={firstName}
                onChange={(event) => setFirstName(event.target.value)}
                fullWidth
              />
              <TextField
                label="Last name"
                value={lastName}
                onChange={(event) => setLastName(event.target.value)}
                fullWidth
              />

              {message ? <Alert severity={message.severity}>{message.text}</Alert> : null}

              <Box>
                <Button
                  variant="contained"
                  onClick={handleSubmit}
                  disabled={isSaving}
                  sx={{
                    bgcolor: "#14532d",
                    fontWeight: 800,
                    borderRadius: 999,
                    "&:hover": { bgcolor: "#0f3f22" },
                  }}
                >
                  {isSaving ? "Saving..." : "Save Settings"}
                </Button>
              </Box>
            </Stack>
          </Paper>

          <Paper
            elevation={0}
            sx={{
              borderRadius: 2,
              border: "1px solid rgba(87, 83, 78, 0.14)",
              bgcolor: "rgba(255, 255, 255, 0.88)",
              boxShadow: "0 24px 80px rgba(28, 25, 23, 0.10)",
              overflow: "hidden",
            }}
          >
            <Stack spacing={1} sx={{ p: { xs: 3, sm: 4 }, pb: 2 }}>
              <Typography variant="h5" sx={{ fontWeight: 800 }}>
                Playlists
              </Typography>
              <Typography color="text.secondary">
                Open a playlist to see the songs saved in it.
              </Typography>
            </Stack>

            {currentUser?.playlists.length ? (
              <List disablePadding>
                {currentUser.playlists.map((playlist, index) => (
                  <ListItem
                    key={playlist.id}
                    disablePadding
                    divider={index < currentUser.playlists.length - 1}
                    secondaryAction={
                      !playlist.is_liked_songs ? (
                        <Button
                          color="error"
                          disabled={deletingPlaylistId === playlist.id}
                          onClick={() => handleDeletePlaylist(playlist.id, playlist.name)}
                          sx={{ fontWeight: 700 }}
                        >
                          {deletingPlaylistId === playlist.id ? "Deleting..." : "Delete"}
                        </Button>
                      ) : undefined
                    }
                  >
                    <ListItemButton
                      onClick={() => navigateToPlaylist(playlist.id)}
                      sx={{ px: { xs: 3, sm: 4 }, py: 1.75 }}
                    >
                      <ListItemText
                        primary={playlist.name}
                        secondary={
                          playlist.is_liked_songs
                            ? "Your default liked songs playlist"
                            : `${playlist.songs.length} songs`
                        }
                      />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            ) : (
              <Box sx={{ px: { xs: 3, sm: 4 }, pb: 4 }}>
                <Typography color="text.secondary">
                  You do not have any playlists yet.
                </Typography>
              </Box>
            )}
          </Paper>
        </Stack>
      </Container>
    </Box>
  );
}
