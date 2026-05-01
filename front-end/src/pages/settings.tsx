import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Container,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { useState } from "react";
import type { AuthenticatedUser } from "../api/auth";
import { updateCurrentUser } from "../api/auth";
import { deletePlaylist } from "../api/playlists";
import AppBrand from "../components/AppBrand";
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
  const [activeTab, setActiveTab] = useState<"account" | "playlists">("account");
  const [email, setEmail] = useState(currentUser?.email ?? "");
  const [firstName, setFirstName] = useState(currentUser?.first_name ?? "");
  const [lastName, setLastName] = useState(currentUser?.last_name ?? "");
  const [isSaving, setIsSaving] = useState(false);
  const [deletingPlaylistId, setDeletingPlaylistId] = useState<number | null>(null);
  const [playlistPendingDelete, setPlaylistPendingDelete] = useState<{
    id: number;
    name: string;
  } | null>(null);
  const [message, setMessage] = useState<{
    severity: "success" | "error";
    text: string;
  } | null>(null);

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
      <Container maxWidth="lg" sx={{ py: { xs: 3, md: 5 } }}>
        <Stack spacing={3}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            alignItems={{ xs: "flex-start", sm: "center" }}
            justifyContent="space-between"
            spacing={2}
          >
            <Stack spacing={1}>
              <AppBrand />
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

          <Box sx={{ maxWidth: 960 }}>
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
              <Tabs
                value={activeTab}
                onChange={(_event, value: "account" | "playlists") => setActiveTab(value)}
                sx={{
                  px: { xs: 2, sm: 3 },
                  pt: 2,
                  "& .MuiTab-root": {
                    alignItems: "flex-start",
                    fontWeight: 800,
                    color: "#6b6257",
                  },
                  "& .Mui-selected": {
                    color: "#14532d",
                  },
                  "& .MuiTabs-indicator": {
                    backgroundColor: "#14532d",
                  },
                }}
              >
                <Tab value="account" label="Account" />
                <Tab value="playlists" label="Playlists" />
              </Tabs>

              {activeTab === "account" ? (
                <Stack spacing={3} sx={{ p: { xs: 3, sm: 4 } }}>
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
              ) : (
                <Stack spacing={1} sx={{ p: { xs: 3, sm: 4 } }}>
                  <Typography variant="h5" sx={{ fontWeight: 800 }}>
                    Playlists
                  </Typography>
                  <Typography color="text.secondary">
                    Open a playlist to see the songs saved in it.
                  </Typography>

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
                                onClick={() =>
                                  setPlaylistPendingDelete({ id: playlist.id, name: playlist.name })
                                }
                                sx={{ fontWeight: 700 }}
                              >
                                {deletingPlaylistId === playlist.id ? "Deleting..." : "Delete"}
                              </Button>
                            ) : undefined
                          }
                        >
                          <ListItemButton
                            onClick={() => navigateToPlaylist(playlist.id)}
                            sx={{ py: 1.75, pr: { xs: 9, sm: 11 } }}
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
                    <Box sx={{ pb: 1 }}>
                      <Typography color="text.secondary">
                        You do not have any playlists yet.
                      </Typography>
                    </Box>
                  )}
                </Stack>
              )}
            </Paper>
          </Box>
        </Stack>
      </Container>
      <Dialog
        open={playlistPendingDelete !== null}
        onClose={() => setPlaylistPendingDelete(null)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>Delete playlist?</DialogTitle>
        <DialogContent>
          <Typography color="text.secondary">
            {playlistPendingDelete
              ? `This will permanently delete ${playlistPendingDelete.name}.`
              : ""}
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button onClick={() => setPlaylistPendingDelete(null)} sx={{ color: "#6b6257" }}>
            Cancel
          </Button>
          <Button
            color="error"
            variant="contained"
            onClick={async () => {
              if (!playlistPendingDelete) {
                return;
              }
              const target = playlistPendingDelete;
              setPlaylistPendingDelete(null);
              await handleDeletePlaylist(target.id, target.name);
            }}
            sx={{ fontWeight: 800, borderRadius: 999 }}
          >
            Delete Playlist
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
