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
import { useEffect, useMemo, useState } from "react";
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
  const [isEditMode, setIsEditMode] = useState(false);
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [draftSongIds, setDraftSongIds] = useState<number[]>([]);
  const [draggingSongId, setDraggingSongId] = useState<number | null>(null);
  const [dragOverSongId, setDragOverSongId] = useState<number | null>(null);
  const [message, setMessage] = useState<{
    severity: "success" | "error";
    text: string;
  } | null>(null);
  const playlistId = Number(new URLSearchParams(search).get("id"));

  const playlist = useMemo(
    () => currentUser?.playlists.find((item) => item.id === playlistId) ?? null,
    [currentUser, playlistId],
  );

  useEffect(() => {
    setDraftSongIds(playlist?.songs ?? []);
  }, [playlist]);

  const displayedSongIds = isEditMode ? draftSongIds : (playlist?.songs ?? []);

  const playlistSongs = useMemo(() => {
    if (!songs) {
      return [];
    }

    return displayedSongIds
      .map((songId) => songs.find((song) => song.id === songId) ?? null)
      .filter((song): song is NonNullable<typeof song> => song !== null);
  }, [displayedSongIds, songs]);

  const addableSongs = useMemo(() => {
    if (!songs) {
      return [];
    }

    return songs.filter((song) => !displayedSongIds.includes(song.id));
  }, [displayedSongIds, songs]);

  const handleHomeClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    navigateTo("/");
  };

  const handleExportPlaylist = () => {
    if (!playlist || !playlistSongs.length) {
      return;
    }

    const escapeCsvValue = (value: string) => `"${value.replaceAll('"', '""')}"`;
    const csvRows = [
      ["playlist", "title", "artists", "key"],
      ...playlistSongs.map((song) => [
        playlist.name,
        song.title,
        song.artists.join(", "),
        song.key,
      ]),
    ];

    const csvContent = csvRows
      .map((row) => row.map((value) => escapeCsvValue(value)).join(","))
      .join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const safePlaylistName = playlist.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

    link.href = downloadUrl;
    link.download = `${safePlaylistName || "playlist"}-export.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(downloadUrl);
  };

  const handleRemoveSong = async (songId: number, songTitle: string) => {
    if (!playlist || !isEditMode) {
      return;
    }

    setMessage(null);
    setDraftSongIds((currentSongIds) => currentSongIds.filter((id) => id !== songId));
    setMessage({
      severity: "success",
      text: `${songTitle} will be removed when you save your edits.`,
    });
  };

  const handleAddSong = async () => {
    if (!playlist || !selectedSong) {
      return;
    }

    setIsAddingSong(true);
    setMessage(null);

    try {
      await updatePlaylist(playlist.id, {
        songs: [...displayedSongIds, selectedSong.id],
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

  const handleReorderSong = async (targetSongId: number) => {
    if (!playlist || !isEditMode || draggingSongId === null || draggingSongId === targetSongId) {
      return;
    }

    const currentIndex = draftSongIds.indexOf(draggingSongId);
    const targetIndex = draftSongIds.indexOf(targetSongId);
    if (currentIndex === -1 || targetIndex === -1) {
      return;
    }

    const nextSongs = [...draftSongIds];
    const [movedSongId] = nextSongs.splice(currentIndex, 1);
    nextSongs.splice(targetIndex, 0, movedSongId);

    setDraftSongIds(nextSongs);
    setDraggingSongId(null);
    setDragOverSongId(null);
  };

  const handleStartEdit = () => {
    setDraftSongIds(playlist?.songs ?? []);
    setIsEditMode(true);
    setMessage(null);
  };

  const handleCancelEdit = () => {
    setDraftSongIds(playlist?.songs ?? []);
    setIsEditMode(false);
    setDraggingSongId(null);
    setDragOverSongId(null);
    setMessage(null);
  };

  const handleSaveEdit = async () => {
    if (!playlist) {
      return;
    }

    setIsSavingEdit(true);
    setMessage(null);

    try {
      await updatePlaylist(playlist.id, { songs: draftSongIds });
      const refreshedUser = await fetchCurrentUser();
      onCurrentUserChange(refreshedUser);
      setIsEditMode(false);
      setMessage({ severity: "success", text: `${playlist.name} was updated.` });
    } catch (_error) {
      setMessage({
        severity: "error",
        text: "We couldn't save your playlist edits right now.",
      });
    } finally {
      setIsSavingEdit(false);
      setDraggingSongId(null);
      setDragOverSongId(null);
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
                onClick={handleExportPlaylist}
                disabled={!playlistSongs.length}
                sx={{
                  borderColor: "rgba(20, 83, 45, 0.28)",
                  color: "#14532d",
                  fontWeight: 700,
                  borderRadius: 999,
                }}
              >
                Export CSV
              </Button>
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
                      disabled={isEditMode}
                      fullWidth
                      getOptionLabel={(song) =>
                        song.artists.length ? `${song.title} - ${song.artists.join(", ")}` : song.title
                      }
                      renderInput={(params) => <TextField {...params} label="Search songs" />}
                    />
                    <Button
                      variant="contained"
                      onClick={handleAddSong}
                      disabled={!selectedSong || isAddingSong || isEditMode}
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
                  {isEditMode ? (
                    <Typography color="text.secondary" sx={{ fontSize: 14 }}>
                      Finish or cancel your current playlist edits before adding more songs.
                    </Typography>
                  ) : null}
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
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  justifyContent="space-between"
                  alignItems={{ xs: "flex-start", sm: "center" }}
                  spacing={1.5}
                  sx={{ px: 3, py: 2.25, borderBottom: "1px solid rgba(87, 83, 78, 0.14)" }}
                >
                  <Box>
                    <Typography variant="h5" sx={{ fontWeight: 800 }}>
                      Songs
                    </Typography>
                    <Typography color="text.secondary">
                      {isEditMode
                        ? "Drag and drop songs to reorder them, then save or cancel your changes."
                        : "Open songs from this playlist, or switch to edit mode to manage them."}
                    </Typography>
                  </Box>
                  {isEditMode ? (
                    <Stack direction="row" spacing={1.25}>
                      <Button onClick={handleCancelEdit} sx={{ color: "#6b6257", fontWeight: 700 }}>
                        Cancel
                      </Button>
                      <Button
                        variant="contained"
                        onClick={handleSaveEdit}
                        disabled={isSavingEdit}
                        sx={{
                          bgcolor: "#14532d",
                          fontWeight: 800,
                          borderRadius: 999,
                          "&:hover": { bgcolor: "#0f3f22" },
                        }}
                      >
                        {isSavingEdit ? "Saving..." : "Save"}
                      </Button>
                    </Stack>
                  ) : (
                    <Button
                      variant="outlined"
                      onClick={handleStartEdit}
                      sx={{
                        borderColor: "rgba(20, 83, 45, 0.28)",
                        color: "#14532d",
                        fontWeight: 700,
                        borderRadius: 999,
                      }}
                    >
                      Edit
                    </Button>
                  )}
                </Stack>
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
                        draggable={isEditMode}
                        onDragStart={() => {
                          if (!isEditMode) {
                            return;
                          }
                          setDraggingSongId(song.id);
                          setDragOverSongId(song.id);
                        }}
                        onDragOver={(event) => {
                          if (!isEditMode) {
                            return;
                          }
                          event.preventDefault();
                          if (draggingSongId !== song.id) {
                            setDragOverSongId(song.id);
                          }
                        }}
                        onDrop={(event) => {
                          if (!isEditMode) {
                            return;
                          }
                          event.preventDefault();
                          void handleReorderSong(song.id);
                        }}
                        onDragEnd={() => {
                          setDraggingSongId(null);
                          setDragOverSongId(null);
                        }}
                        sx={{
                          opacity: draggingSongId === song.id ? 0.6 : 1,
                          bgcolor:
                            dragOverSongId === song.id && draggingSongId !== song.id
                              ? "rgba(20, 83, 45, 0.06)"
                              : "transparent",
                          transition: "background-color 120ms ease",
                        }}
                        secondaryAction={
                          isEditMode ? (
                            <Button
                              color="error"
                              onClick={() => handleRemoveSong(song.id, song.title)}
                              sx={{ fontWeight: 700 }}
                            >
                              Remove
                            </Button>
                          ) : undefined
                        }
                      >
                        <ListItemButton
                          onClick={() => {
                            if (!isEditMode) {
                              navigateToSong(song.key);
                            }
                          }}
                          sx={{
                            py: 1.6,
                            cursor: isEditMode ? "grab" : "pointer",
                          }}
                        >
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
