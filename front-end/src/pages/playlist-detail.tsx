import {
  Autocomplete,
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
import { useMemo, useState } from "react";
import type { AuthenticatedUser } from "../api/auth";
import { fetchCurrentUser } from "../api/auth";
import { updatePlaylist } from "../api/playlists";
import ProfileMenu, { ProfileAvatarButton } from "../components/ProfileMenu";
import { useAllSongs } from "../api/hooks/songs";
import type { SongType } from "../types/songs";
import { navigateTo, navigateToSong } from "../utils/navigation";

type PlaylistDetailPageProps = {
  currentUser: AuthenticatedUser | null;
  onCurrentUserChange: (user: AuthenticatedUser) => void;
  onLogout: () => void;
  search: string;
};

export default function PlaylistDetailPage({
  currentUser,
  onCurrentUserChange,
  onLogout,
  search,
}: PlaylistDetailPageProps) {
  const { data: songs, isLoading } = useAllSongs();
  const [profileMenuAnchor, setProfileMenuAnchor] = useState<HTMLElement | null>(null);
  const [selectedSong, setSelectedSong] = useState<SongType | null>(null);
  const [isAddingSong, setIsAddingSong] = useState(false);
  const [removingSongId, setRemovingSongId] = useState<number | null>(null);
  const [message, setMessage] = useState<{
    severity: "success" | "error";
    text: string;
  } | null>(null);
  const playlistId = Number(new URLSearchParams(search).get("id"));

  const playlist = useMemo(
    () => currentUser?.playlists.find((item) => item.id === playlistId) ?? null,
    [currentUser, playlistId],
  );

  const playlistSongs = useMemo(() => {
    if (!playlist || !songs) {
      return [];
    }

    return playlist.songs
      .map((songId) => songs.find((song) => song.id === songId) ?? null)
      .filter((song): song is NonNullable<typeof song> => song !== null);
  }, [playlist, songs]);

  const addableSongs = useMemo(() => {
    if (!playlist || !songs) {
      return [];
    }

    return songs.filter((song) => !playlist.songs.includes(song.id));
  }, [playlist, songs]);

  const handleHomeClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    navigateTo("/");
  };

  const handleRemoveSong = async (songId: number, songTitle: string) => {
    if (!playlist) {
      return;
    }

    setRemovingSongId(songId);
    setMessage(null);

    try {
      await updatePlaylist(playlist.id, {
        songs: playlist.songs.filter((id) => id !== songId),
      });
      const refreshedUser = await fetchCurrentUser();
      onCurrentUserChange(refreshedUser);
      setMessage({ severity: "success", text: `${songTitle} was removed from ${playlist.name}.` });
    } catch (_error) {
      setMessage({
        severity: "error",
        text: `We couldn't remove ${songTitle} right now.`,
      });
    } finally {
      setRemovingSongId(null);
    }
  };

  const handleAddSong = async () => {
    if (!playlist || !selectedSong) {
      return;
    }

    setIsAddingSong(true);
    setMessage(null);

    try {
      await updatePlaylist(playlist.id, {
        songs: [...playlist.songs, selectedSong.id],
      });
      const refreshedUser = await fetchCurrentUser();
      onCurrentUserChange(refreshedUser);
      setMessage({ severity: "success", text: `${selectedSong.title} was added to ${playlist.name}.` });
      setSelectedSong(null);
    } catch (_error) {
      setMessage({
        severity: "error",
        text: `We couldn't add ${selectedSong.title} right now.`,
      });
    } finally {
      setIsAddingSong(false);
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
              <Typography variant="h2">{playlist?.name ?? "Playlist"}</Typography>
              {playlist ? (
                <Typography color="text.secondary">
                  {playlist.is_liked_songs
                    ? "Your default liked songs playlist"
                    : `${playlistSongs.length} saved songs`}
                </Typography>
              ) : null}
            </Stack>
            <Stack direction="row" spacing={1.5} useFlexGap flexWrap="wrap">
              <Button
                variant="outlined"
                onClick={() => navigateTo("/settings")}
                sx={{
                  borderColor: "rgba(20, 83, 45, 0.28)",
                  color: "#14532d",
                  fontWeight: 700,
                  borderRadius: 999,
                }}
              >
                Back to Settings
              </Button>
              <ProfileAvatarButton
                currentUser={currentUser}
                onClick={(event) => setProfileMenuAnchor(event.currentTarget)}
              />
            </Stack>
          </Stack>

          {!playlist ? (
            <Alert severity="warning">We couldn't find that playlist.</Alert>
          ) : (
            <Stack spacing={2}>
              {message ? <Alert severity={message.severity}>{message.text}</Alert> : null}
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
                <Stack spacing={2}>
                  <Box>
                    <Typography variant="h5" sx={{ fontWeight: 800 }}>
                      Add songs
                    </Typography>
                    <Typography color="text.secondary">
                      Search the archive and add songs directly to this playlist.
                    </Typography>
                  </Box>
                  <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                    <Autocomplete
                      options={addableSongs}
                      value={selectedSong}
                      onChange={(_event, value) => setSelectedSong(value)}
                      fullWidth
                      getOptionLabel={(song) =>
                        song.artists.length ? `${song.title} - ${song.artists.join(", ")}` : song.title
                      }
                      renderInput={(params) => <TextField {...params} label="Search songs" />}
                    />
                    <Button
                      variant="contained"
                      onClick={handleAddSong}
                      disabled={!selectedSong || isAddingSong}
                      sx={{
                        minWidth: 140,
                        bgcolor: "#14532d",
                        fontWeight: 800,
                        borderRadius: 999,
                        "&:hover": { bgcolor: "#0f3f22" },
                      }}
                    >
                      {isAddingSong ? "Adding..." : "Add Song"}
                    </Button>
                  </Stack>
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
                {isLoading ? (
                  <Box sx={{ p: 3 }}>
                    <Typography color="text.secondary">Loading playlist songs...</Typography>
                  </Box>
                ) : playlistSongs.length ? (
                  <List disablePadding>
                    {playlistSongs.map((song, index) => (
                      <ListItem
                        key={song.id}
                        disablePadding
                        divider={index < playlistSongs.length - 1}
                        secondaryAction={
                          <Button
                            color="error"
                            disabled={removingSongId === song.id}
                            onClick={() => handleRemoveSong(song.id, song.title)}
                            sx={{ fontWeight: 700 }}
                          >
                            {removingSongId === song.id ? "Removing..." : "Remove"}
                          </Button>
                        }
                      >
                        <ListItemButton onClick={() => navigateToSong(song.key)} sx={{ py: 1.6 }}>
                          <ListItemText
                            primary={song.title}
                            secondary={song.artists.length ? song.artists.join(", ") : "Unknown artist"}
                          />
                        </ListItemButton>
                      </ListItem>
                    ))}
                  </List>
                ) : (
                  <Box sx={{ p: 3 }}>
                    <Typography color="text.secondary">
                      This playlist does not have any songs yet.
                    </Typography>
                  </Box>
                )}
              </Paper>
            </Stack>
          )}
        </Stack>
      </Container>
      <ProfileMenu
        currentUser={currentUser}
        onLogout={onLogout}
        anchorEl={profileMenuAnchor}
        onClose={() => setProfileMenuAnchor(null)}
      />
    </Box>
  );
}
