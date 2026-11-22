import {
  Alert,
  Box,
  Button,
  Container,
  Divider,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Link,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useState } from "react";
import SongInputComponent from "../sections/SongInput";
import SongSuggestionSlider from "../sections/SongSuggestion";
import { useRecentlyOpenedSongs } from "../api/hooks/songs";
import SongContext from "../contexts/SongContext";
import Footer from "../sections/Footer";
import { playlistPath, handleInternalLinkClick } from "../utils/navigation";
import type { AuthenticatedUser } from "../api/auth";
import { fetchCurrentUser } from "../api/auth";
import { createPlaylist } from "../api/playlists";
import AppBrand from "../components/AppBrand";
import ProfileMenu, { ProfileAvatarButton } from "../components/ProfileMenu";

type MainPageProps = {
  currentUser: AuthenticatedUser | null;
  onCurrentUserChange: (user: AuthenticatedUser) => void;
  onLogout: () => void;
};

export default function MainPage({
  currentUser,
  onCurrentUserChange,
  onLogout,
}: MainPageProps) {
  const { data: recentSongs, isLoading: areRecentSongsLoading } =
    useRecentlyOpenedSongs();
  const catalogueStats = currentUser?.catalogue_stats;
  const [profileMenuAnchor, setProfileMenuAnchor] =
    useState<HTMLElement | null>(null);
  const [isCreatePlaylistOpen, setIsCreatePlaylistOpen] = useState(false);
  const [newPlaylistName, setNewPlaylistName] = useState("");
  const [isCreatingPlaylist, setIsCreatingPlaylist] = useState(false);
  const [playlistMessage, setPlaylistMessage] = useState<string | null>(null);

  const handleCreatePlaylist = async () => {
    const name = newPlaylistName.trim();
    if (!name) {
      setPlaylistMessage("Choose a name for the playlist.");
      return;
    }
    setIsCreatingPlaylist(true);
    setPlaylistMessage(null);
    try {
      await createPlaylist({ name, songs: [] });
      onCurrentUserChange(await fetchCurrentUser());
      setNewPlaylistName("");
      setIsCreatePlaylistOpen(false);
    } catch (_error) {
      setPlaylistMessage("We couldn't create that playlist right now.");
    } finally {
      setIsCreatingPlaylist(false);
    }
  };

  return (
    <SongContext
      value={{ data: recentSongs, isLoading: areRecentSongsLoading }}
    >
      <Box
        sx={{
          minHeight: "100vh",
          background:
            "linear-gradient(145deg, #f7f3ed 0%, #eef4ee 46%, #f8efe7 100%)",
        }}
      >
        <Container maxWidth="lg" sx={{ py: { xs: 3, md: 5 } }}>
          <Stack spacing={{ xs: 4, md: 6 }}>
            <Stack
              component="header"
              direction="row"
              alignItems="center"
              justifyContent="space-between"
              spacing={2}
            >
              <AppBrand />

              <Stack
                direction="row"
                alignItems="center"
                spacing={{ xs: 1.5, sm: 2.5 }}
                useFlexGap
                flexWrap="wrap"
                justifyContent="flex-end"
              >
                <Link
                  href="/books"
                  underline="none"
                  onClick={(event) => handleInternalLinkClick(event, "/books")}
                  sx={{
                    border: 0,
                    bgcolor: "transparent",
                    color: "#14532d",
                    cursor: "pointer",
                    fontWeight: 700,
                    p: 0,
                  }}
                >
                  Books
                </Link>
                <Link
                  href="/songs"
                  underline="none"
                  onClick={(event) => handleInternalLinkClick(event, "/songs")}
                  sx={{
                    border: 0,
                    bgcolor: "transparent",
                    color: "#14532d",
                    cursor: "pointer",
                    fontWeight: 700,
                    p: 0,
                  }}
                >
                  All Songs A-Z
                </Link>
                <ProfileAvatarButton
                  currentUser={currentUser}
                  onClick={(event) => setProfileMenuAnchor(event.currentTarget)}
                />
              </Stack>
            </Stack>

            <Box
              component="main"
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr",
                  md: "minmax(0, 1.1fr) 360px",
                },
                gap: { xs: 3, md: 4 },
                alignItems: "stretch",
              }}
            >
              <Paper
                elevation={0}
                sx={{
                  p: { xs: 3, sm: 4, md: 5 },
                  borderRadius: 2,
                  border: "1px solid rgba(87, 83, 78, 0.14)",
                  bgcolor: "rgba(255, 255, 255, 0.86)",
                  boxShadow: "0 24px 80px rgba(28, 25, 23, 0.10)",
                }}
              >
                <Stack spacing={4}>
                  <Stack spacing={2}>
                    <Typography
                      variant="h2"
                      sx={{
                        maxWidth: 680,
                        fontWeight: 850,
                        fontSize: { xs: "2.45rem", sm: "3.4rem", md: "4.5rem" },
                        lineHeight: 0.95,
                      }}
                    >
                      Find the chart you want to play.
                    </Typography>
                    <Typography
                      color="text.secondary"
                      sx={{ maxWidth: 620, fontSize: { xs: 17, md: 19 } }}
                    >
                      Search the Brasileiro archive and open the original PDF
                      score in one step.
                    </Typography>
                  </Stack>

                  <SongInputComponent />
                </Stack>
              </Paper>

              <Paper
                elevation={0}
                sx={{
                  p: 3,
                  borderRadius: 2,
                  border: "1px solid rgba(20, 83, 45, 0.16)",
                  bgcolor: "#17351f",
                  color: "#fffaf3",
                  minHeight: { xs: 220, md: "100%" },
                  display: "flex",
                }}
              >
                <Stack spacing={2.5} sx={{ width: "100%" }}>
                  <Typography sx={{ color: "rgba(255, 250, 243, 0.7)" }}>
                    Archive snapshot
                  </Typography>
                  <Stack spacing={2}>
                    <Typography variant="h3" sx={{ fontWeight: 850 }}>
                      {catalogueStats?.songs ?? "--"}
                    </Typography>
                    <Typography sx={{ color: "rgba(255, 250, 243, 0.76)" }}>
                      searchable scores in the current collection.
                    </Typography>
                  </Stack>
                  <Divider sx={{ borderColor: "rgba(255, 250, 243, 0.18)" }} />
                  <Stack direction="row" spacing={4}>
                    <Box>
                      <Typography variant="h5" sx={{ fontWeight: 800 }}>
                        {catalogueStats?.artists ?? "--"}
                      </Typography>
                      <Typography sx={{ color: "rgba(255, 250, 243, 0.68)" }}>
                        artists
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="h5" sx={{ fontWeight: 800 }}>
                        {catalogueStats?.books ?? "--"}
                      </Typography>
                      <Typography sx={{ color: "rgba(255, 250, 243, 0.68)" }}>
                        books
                      </Typography>
                    </Box>
                  </Stack>
                </Stack>
              </Paper>
            </Box>

            <Stack spacing={2.5}>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                justifyContent="space-between"
                spacing={1}
              >
                <Box>
                  <Typography variant="h4" sx={{ fontWeight: 800 }}>
                    Recently opened
                  </Typography>
                  <Typography color="text.secondary">
                    Your latest songs, ready to reopen.
                  </Typography>
                </Box>
              </Stack>
              <SongSuggestionSlider />
            </Stack>

            <Stack spacing={2.5}>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                justifyContent="space-between"
                alignItems={{ xs: "flex-start", sm: "center" }}
                spacing={1.5}
              >
                <Box>
                  <Typography variant="h4" sx={{ fontWeight: 800 }}>
                    Your playlists
                  </Typography>
                  <Typography color="text.secondary">
                    Personal and shared collections, ready to play together.
                  </Typography>
                </Box>
                <Button
                  variant="contained"
                  onClick={() => setIsCreatePlaylistOpen(true)}
                  sx={{
                    bgcolor: "#14532d",
                    fontWeight: 800,
                    borderRadius: 999,
                    "&:hover": { bgcolor: "#0f3f22" },
                  }}
                >
                  New Playlist
                </Button>
              </Stack>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "1fr",
                    sm: "repeat(2, minmax(0, 1fr))",
                    md: "repeat(3, minmax(0, 1fr))",
                  },
                  gap: 2,
                }}
              >
                {(currentUser?.playlists ?? []).map((playlist) => {
                  const href = playlistPath(playlist.id);
                  const sharingLabel = playlist.is_owner
                    ? playlist.members.length
                      ? `Shared with ${playlist.members.length} ${playlist.members.length === 1 ? "person" : "people"}`
                      : "Private playlist"
                    : `Shared by ${playlist.owner.display_name}`;
                  return (
                    <Paper
                      key={playlist.id}
                      component="a"
                      href={href}
                      onClick={(event) => handleInternalLinkClick(event, href)}
                      elevation={0}
                      sx={{
                        p: 2.5,
                        color: "inherit",
                        textDecoration: "none",
                        borderRadius: 2,
                        border: "1px solid rgba(20, 83, 45, 0.16)",
                        bgcolor: "rgba(255, 255, 255, 0.82)",
                        transition:
                          "transform 140ms ease, box-shadow 140ms ease",
                        "&:hover": {
                          transform: "translateY(-2px)",
                          boxShadow: "0 16px 38px rgba(28, 25, 23, 0.1)",
                        },
                      }}
                    >
                      <Stack spacing={0.75}>
                        <Typography variant="h6" sx={{ fontWeight: 800 }}>
                          {playlist.name}
                        </Typography>
                        <Typography color="text.secondary">
                          {playlist.songs.length}{" "}
                          {playlist.songs.length === 1 ? "song" : "songs"}
                        </Typography>
                        <Typography
                          sx={{
                            color: "#14532d",
                            fontSize: 14,
                            fontWeight: 700,
                          }}
                        >
                          {playlist.is_liked_songs
                            ? "Your liked songs"
                            : sharingLabel}
                        </Typography>
                      </Stack>
                    </Paper>
                  );
                })}
              </Box>
            </Stack>

            <Footer />
          </Stack>
        </Container>
        <ProfileMenu
          currentUser={currentUser}
          onLogout={onLogout}
          anchorEl={profileMenuAnchor}
          onClose={() => setProfileMenuAnchor(null)}
        />
        <Dialog
          open={isCreatePlaylistOpen}
          onClose={() => setIsCreatePlaylistOpen(false)}
          fullWidth
          maxWidth="xs"
        >
          <DialogTitle>Create playlist</DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ pt: 1 }}>
              {playlistMessage ? (
                <Alert severity="error">{playlistMessage}</Alert>
              ) : null}
              <TextField
                autoFocus
                label="Playlist name"
                value={newPlaylistName}
                onChange={(event) => setNewPlaylistName(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    void handleCreatePlaylist();
                  }
                }}
              />
            </Stack>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 3 }}>
            <Button onClick={() => setIsCreatePlaylistOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="contained"
              disabled={isCreatingPlaylist}
              onClick={handleCreatePlaylist}
              sx={{ bgcolor: "#14532d", "&:hover": { bgcolor: "#0f3f22" } }}
            >
              {isCreatingPlaylist ? "Creating..." : "Create"}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </SongContext>
  );
}
