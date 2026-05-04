import {
  Alert,
  Autocomplete,
  Box,
  Button,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  Link,
  Stack,
  Switch,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useEffect, useMemo, useState } from "react";
import type { AuthenticatedUser, Playlist } from "../api/auth";
import { fetchCurrentUser } from "../api/auth";
import { createPlaylist, updatePlaylist } from "../api/playlists";
import {
  updateSongMetadata,
  useAllSongs,
  useArtists,
  useSong,
  useSongUrls,
} from "../api/hooks/songs";
import AppBrand from "../components/AppBrand";
import ProfileMenu, { ProfileAvatarButton } from "../components/ProfileMenu";
import { navigateTo } from "../utils/navigation";

type SongDetailPageProps = {
  currentUser: AuthenticatedUser | null;
  onCurrentUserChange: (user: AuthenticatedUser) => void;
  onLogout: () => void;
  search: string;
};

const pdfFrameWidth = "min(100%, 920px)";

export default function SongDetailPage({
  currentUser,
  onCurrentUserChange,
  onLogout,
  search,
}: SongDetailPageProps) {
  const searchParams = new URLSearchParams(search);
  const songId = Number(searchParams.get("id"));
  const versionIdFromUrl = Number(searchParams.get("version"));
  const legacySongKey = searchParams.get("key");
  const {
    data: songs,
    isLoading: isSongsLoading,
    mutate: refreshSong,
  } = useSong(songId || null, legacySongKey);
  const song = songs?.[0] ?? null;
  const isStaff = currentUser?.is_staff === true;
  const { data: artists } = useArtists(isStaff);
  const { data: allSongs } = useAllSongs(undefined, isStaff);
  const initialVersion =
    song?.versions.find((version) => version.id === versionIdFromUrl) ??
    song?.versions[0] ??
    null;
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(
    initialVersion?.id ?? null,
  );
  const selectedVersion =
    song?.versions.find((version) => version.id === selectedVersionId) ??
    initialVersion;
  const selectedBook = selectedVersion?.book ?? null;
  const { data: songUrls, isLoading: isPdfLoading } = useSongUrls(
    song?.versions ?? [],
  );
  const songUrl = selectedVersion ? songUrls[selectedVersion.id] : undefined;
  const [isPlaylistDialogOpen, setIsPlaylistDialogOpen] = useState(false);
  const [newPlaylistName, setNewPlaylistName] = useState("");
  const [activePlaylistId, setActivePlaylistId] = useState<number | null>(null);
  const [isCreatingPlaylist, setIsCreatingPlaylist] = useState(false);
  const [profileMenuAnchor, setProfileMenuAnchor] = useState<HTMLElement | null>(null);
  const [isEditSongDialogOpen, setIsEditSongDialogOpen] = useState(false);
  const [selectedTitle, setSelectedTitle] = useState("");
  const [useCustomTitle, setUseCustomTitle] = useState(false);
  const [customTitle, setCustomTitle] = useState("");
  const [selectedArtistNames, setSelectedArtistNames] = useState<string[]>([]);
  const [useCustomArtists, setUseCustomArtists] = useState(false);
  const [customArtistsText, setCustomArtistsText] = useState("");
  const [isSavingSongMetadata, setIsSavingSongMetadata] = useState(false);
  const [playlistMessage, setPlaylistMessage] = useState<{
    severity: "success" | "error";
    text: string;
  } | null>(null);
  const [songMetadataMessage, setSongMetadataMessage] = useState<{
    severity: "success" | "error";
    text: string;
  } | null>(null);

  const availablePlaylists = useMemo(() => currentUser?.playlists ?? [], [currentUser]);
  const songVersionIds = useMemo(
    () => song?.versions.map((version) => version.id) ?? [],
    [song],
  );
  const artistOptions = useMemo(
    () => artists.map((artist) => artist.name),
    [artists],
  );
  const titleOptions = useMemo(
    () => Array.from(new Set((allSongs ?? []).map((song) => song.title))).sort(),
    [allSongs],
  );

  useEffect(() => {
    setSelectedVersionId(initialVersion?.id ?? null);
  }, [initialVersion?.id]);

  const handleAllSongsClick = () => {
    navigateTo("/songs");
  };

  const handleOpenYoutube = () => {
    if (!song) {
      return;
    }

    const searchQuery = [song.title, ...song.artists, "youtube"].filter(Boolean).join(" ");
    const youtubeUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(searchQuery)}`;
    window.open(youtubeUrl, "_blank", "noopener,noreferrer");
  };

  const handleOpenPdfInNewTab = () => {
    if (!songUrl) {
      return;
    }

    window.open(songUrl, "_blank", "noopener,noreferrer");
  };

  const handleStartEditSong = () => {
    if (!song) {
      return;
    }

    setSelectedTitle(song.title);
    setCustomTitle(song.title);
    setUseCustomTitle(false);
    setSelectedArtistNames(song.artists);
    setCustomArtistsText(song.artists.join(", "));
    setUseCustomArtists(false);
    setSongMetadataMessage(null);
    setIsEditSongDialogOpen(true);
  };

  const getDraftArtistText = () => {
    if (useCustomArtists) {
      return customArtistsText
        .split(",")
        .map((artist) => artist.trim())
        .filter(Boolean)
        .join(", ");
    }

    return selectedArtistNames
      .map((artist) => artist.trim())
      .filter(Boolean)
      .join(", ");
  };

  const getDraftTitle = () => {
    if (useCustomTitle) {
      return customTitle.trim();
    }

    return selectedTitle.trim();
  };

  const handleSaveSongMetadata = async () => {
    if (!song) {
      return;
    }

    const nextTitle = getDraftTitle();
    const nextArtistText = getDraftArtistText();
    if (!nextTitle || !nextArtistText) {
      setSongMetadataMessage({
        severity: "error",
        text: "Title and artists are required.",
      });
      return;
    }

    setIsSavingSongMetadata(true);
    setSongMetadataMessage(null);

    try {
      await updateSongMetadata(song.id, {
        title: nextTitle,
        artist: nextArtistText,
      });
      await refreshSong();
      setIsEditSongDialogOpen(false);
      setSongMetadataMessage({
        severity: "success",
        text: "Song details updated.",
      });
    } catch (_error) {
      setSongMetadataMessage({
        severity: "error",
        text: "We couldn't update those song details right now.",
      });
    } finally {
      setIsSavingSongMetadata(false);
    }
  };

  const syncCurrentUser = async () => {
    const refreshedUser = await fetchCurrentUser();
    onCurrentUserChange(refreshedUser);
  };

  const updatePlaylistSongs = async (
    playlist: Playlist,
    nextSongIds: number[],
    successMessage: string,
  ) => {
    await updatePlaylist(playlist.id, { songs: nextSongIds });
    await syncCurrentUser();
    setPlaylistMessage({ severity: "success", text: successMessage });
  };

  const handleAddToExistingPlaylist = async (playlist: Playlist) => {
    if (!song || playlist.songs.some((songId) => songVersionIds.includes(songId))) {
      return;
    }

    setActivePlaylistId(playlist.id);
    setPlaylistMessage(null);

    try {
      await updatePlaylistSongs(
        playlist,
        [...playlist.songs, song.id],
        `"${song.title}" added to ${playlist.name}.`,
      );
    } catch (_error) {
      setPlaylistMessage({
        severity: "error",
        text: `We couldn't add this song to ${playlist.name}.`,
      });
    } finally {
      setActivePlaylistId(null);
    }
  };

  const handleCreatePlaylist = async () => {
    if (!song) {
      return;
    }

    const trimmedName = newPlaylistName.trim();
    if (!trimmedName) {
      setPlaylistMessage({
        severity: "error",
        text: "Choose a name for the new playlist.",
      });
      return;
    }

    setIsCreatingPlaylist(true);
    setPlaylistMessage(null);

    try {
      await createPlaylist({ name: trimmedName, songs: [song.id] });
      await syncCurrentUser();
      setNewPlaylistName("");
      setIsPlaylistDialogOpen(false);
      setPlaylistMessage({
        severity: "success",
        text: `"${song.title}" added to your new playlist, ${trimmedName}.`,
      });
    } catch (_error) {
      setPlaylistMessage({
        severity: "error",
        text: "We couldn't create that playlist right now.",
      });
    } finally {
      setIsCreatingPlaylist(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background:
          "linear-gradient(145deg, #f7f3ed 0%, #eef4ee 46%, #f8efe7 100%)",
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
                component="button"
                type="button"
                underline="none"
                onClick={handleAllSongsClick}
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

          {isSongsLoading ? (
            <Stack spacing={2} alignItems="center" sx={{ py: 8 }}>
              <CircularProgress size={34} sx={{ color: "#14532d" }} />
              <Typography color="text.secondary">Loading song details...</Typography>
            </Stack>
          ) : (!songId && !legacySongKey) || song == null ? (
            <Stack spacing={2}>
              <Alert severity="warning">
                We couldn't find that song in the archive listing.
              </Alert>
              <Box>
                <Button
                  variant="contained"
                  onClick={handleAllSongsClick}
                  sx={{
                    bgcolor: "#14532d",
                    fontWeight: 800,
                    borderRadius: 999,
                    "&:hover": { bgcolor: "#0f3f22" },
                  }}
                >
                  Return to All Songs
                </Button>
              </Box>
            </Stack>
          ) : (
            <Stack spacing={2.5} alignItems="center">
              <Stack spacing={1} sx={{ width: pdfFrameWidth, maxWidth: "100%" }}>
                <Stack
                  direction="row"
                  alignItems="flex-start"
                  spacing={1}
                  sx={{ maxWidth: "100%" }}
                >
                  <Typography
                    variant="h2"
                    sx={{
                      fontWeight: 850,
                      lineHeight: 0.95,
                      fontSize: { xs: "2.4rem", md: "3.8rem" },
                      minWidth: 0,
                      overflowWrap: "anywhere",
                    }}
                  >
                    {song.title}
                  </Typography>
                  {isStaff ? (
                    <IconButton
                      aria-label="Edit song details"
                      onClick={handleStartEditSong}
                      size="small"
                      sx={{
                        color: "#14532d",
                        border: "1px solid rgba(20, 83, 45, 0.28)",
                        mt: { xs: 0.35, md: 0.75 },
                        flex: "0 0 auto",
                        "&:hover": { bgcolor: "rgba(20, 83, 45, 0.08)" },
                      }}
                    >
                      <Box
                        component="svg"
                        aria-hidden="true"
                        viewBox="0 0 24 24"
                        sx={{
                          width: 18,
                          height: 18,
                          fill: "none",
                          stroke: "currentColor",
                          strokeWidth: 2,
                          strokeLinecap: "round",
                          strokeLinejoin: "round",
                        }}
                      >
                        <path d="M12 20h9" />
                        <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
                      </Box>
                    </IconButton>
                  ) : null}
                </Stack>
                <Typography color="text.secondary" sx={{ fontSize: { xs: 17, md: 20 } }}>
                  {song.artists.length ? song.artists.join(", ") : "Unknown artist"}
                </Typography>
                {selectedBook ? (
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    {selectedBook.cover_image ? (
                      <Box
                        component="img"
                        src={selectedBook.cover_image}
                        alt=""
                        sx={{
                          width: 46,
                          height: 62,
                          objectFit: "cover",
                          borderRadius: 1,
                          border: "1px solid rgba(87, 83, 78, 0.16)",
                        }}
                      />
                    ) : null}
                    <Typography color="text.secondary" sx={{ fontWeight: 700 }}>
                      {selectedBook.title}
                      {selectedVersion?.book_song_index
                        ? ` #${selectedVersion.book_song_index}`
                        : ""}
                    </Typography>
                  </Stack>
                ) : null}
                {songMetadataMessage && !isEditSongDialogOpen ? (
                  <Alert severity={songMetadataMessage.severity}>
                    {songMetadataMessage.text}
                  </Alert>
                ) : null}
                {song.versions.length > 1 ? (
                  <Stack spacing={1} sx={{ pt: 1 }}>
                    <Typography
                      variant="caption"
                      sx={{ color: "text.secondary", fontWeight: 800 }}
                    >
                      Versions
                    </Typography>
                    <ToggleButtonGroup
                      exclusive
                      value={selectedVersion?.id ?? null}
                      onChange={(_event, value: number | null) => {
                        if (value == null) {
                          return;
                        }
                        setSelectedVersionId(value);
                      }}
                      size="small"
                      sx={{
                        flexWrap: "wrap",
                        gap: 1,
                        "& .MuiToggleButtonGroup-grouped": {
                          borderRadius: 999,
                          border: "1px solid rgba(20, 83, 45, 0.28)",
                          color: "#14532d",
                          fontWeight: 800,
                          px: 2,
                          "&.Mui-selected": {
                            bgcolor: "#14532d",
                            color: "#fffaf3",
                            "&:hover": { bgcolor: "#0f3f22" },
                          },
                        },
                      }}
                    >
                      {song.versions.map((version) => (
                        <ToggleButton key={version.id} value={version.id}>
                          Version {version.version}
                        </ToggleButton>
                      ))}
                    </ToggleButtonGroup>
                  </Stack>
                ) : null}
              </Stack>

              <Stack spacing={1.5} sx={{ width: pdfFrameWidth, maxWidth: "100%" }}>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                  <Button
                    variant="outlined"
                    onClick={() => setIsPlaylistDialogOpen(true)}
                    sx={{
                      alignSelf: "flex-start",
                      borderColor: "rgba(20, 83, 45, 0.28)",
                      color: "#14532d",
                      fontWeight: 800,
                      borderRadius: 999,
                      px: 2.5,
                    }}
                  >
                    Add to Playlist
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={handleOpenYoutube}
                    sx={{
                      alignSelf: "flex-start",
                      borderColor: "rgba(20, 83, 45, 0.28)",
                      color: "#14532d",
                      fontWeight: 800,
                      borderRadius: 999,
                      px: 2.5,
                    }}
                  >
                    Open on YouTube
                  </Button>
                  <Button
                    variant="contained"
                    onClick={handleOpenPdfInNewTab}
                    disabled={!songUrl}
                    sx={{
                      alignSelf: "flex-start",
                      bgcolor: "#14532d",
                      fontWeight: 800,
                      borderRadius: 999,
                      px: 2.5,
                      "&:hover": { bgcolor: "#0f3f22" },
                    }}
                  >
                    Open PDF in New Tab
                  </Button>
                </Stack>
                {playlistMessage ? (
                  <Alert severity={playlistMessage.severity}>{playlistMessage.text}</Alert>
                ) : null}
              </Stack>

              <Box
                sx={{
                  width: pdfFrameWidth,
                  maxWidth: "100%",
                  position: "relative",
                  borderRadius: 3,
                  overflow: "hidden",
                  border: "1px solid rgba(87, 83, 78, 0.14)",
                  bgcolor: "#ffffff",
                  aspectRatio: "8.5 / 11.4",
                  minHeight: { xs: "110vh", md: "auto" },
                }}
              >
                {songUrl ? (
                  song.versions.map((version) => {
                    const versionUrl = songUrls[version.id];
                    const isSelectedVersion = version.id === selectedVersion?.id;

                    if (!versionUrl) {
                      return null;
                    }

                    return (
                      <Box
                        key={version.id}
                        component="iframe"
                        src={versionUrl}
                        title={`${song.title} version ${version.version} PDF`}
                        aria-hidden={!isSelectedVersion}
                        sx={{
                          width: "100%",
                          height: "100%",
                          border: 0,
                          display: "block",
                          position: isSelectedVersion ? "relative" : "absolute",
                          inset: 0,
                          opacity: isSelectedVersion ? 1 : 0,
                          pointerEvents: isSelectedVersion ? "auto" : "none",
                          visibility: isSelectedVersion ? "visible" : "hidden",
                          zIndex: isSelectedVersion ? 1 : 0,
                        }}
                      />
                    );
                  })
                ) : (
                  <Stack spacing={2} alignItems="center" justifyContent="center" sx={{ py: 10 }}>
                    {isPdfLoading ? (
                      <>
                        <CircularProgress size={34} sx={{ color: "#14532d" }} />
                        <Typography color="text.secondary">Loading sheet music...</Typography>
                      </>
                    ) : (
                      <Alert severity="error" sx={{ width: "100%", maxWidth: 520 }}>
                        We couldn't load the PDF for this song right now.
                      </Alert>
                    )}
                  </Stack>
                )}
              </Box>
            </Stack>
          )}
        </Stack>
      </Container>

      <Dialog
        open={isEditSongDialogOpen}
        onClose={() => {
          if (!isSavingSongMetadata) {
            setIsEditSongDialogOpen(false);
          }
        }}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Edit Song Details</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ pt: 1 }}>
            {songMetadataMessage ? (
              <Alert severity={songMetadataMessage.severity}>
                {songMetadataMessage.text}
              </Alert>
            ) : null}
            <Stack spacing={1.25}>
              <Autocomplete
                options={titleOptions}
                value={selectedTitle}
                disabled={useCustomTitle}
                onChange={(_event, value) => setSelectedTitle(value ?? "")}
                noOptionsText="No matching titles"
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Song title"
                    placeholder="Choose a standardized title"
                  />
                )}
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={useCustomTitle}
                    onChange={(event) => {
                      setUseCustomTitle(event.target.checked);
                      if (event.target.checked) {
                        setCustomTitle(selectedTitle);
                      }
                    }}
                    sx={{
                      "& .MuiSwitch-switchBase.Mui-checked": { color: "#14532d" },
                      "& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track": {
                        bgcolor: "#14532d",
                      },
                    }}
                  />
                }
                label="Create new title"
              />
              {useCustomTitle ? (
                <TextField
                  label="New song title"
                  value={customTitle}
                  onChange={(event) => setCustomTitle(event.target.value)}
                  placeholder="Triste"
                  fullWidth
                />
              ) : null}
            </Stack>
            <Stack spacing={1.25}>
              <Autocomplete
                multiple
                options={artistOptions}
                value={selectedArtistNames}
                disabled={useCustomArtists}
                onChange={(_event, value) => setSelectedArtistNames(value)}
                filterSelectedOptions
                noOptionsText="No matching artists"
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Artists"
                    placeholder="Choose standardized artist names"
                  />
                )}
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={useCustomArtists}
                    onChange={(event) => {
                      setUseCustomArtists(event.target.checked);
                      if (event.target.checked) {
                        setCustomArtistsText(selectedArtistNames.join(", "));
                      }
                    }}
                    sx={{
                      "& .MuiSwitch-switchBase.Mui-checked": { color: "#14532d" },
                      "& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track": {
                        bgcolor: "#14532d",
                      },
                    }}
                  />
                }
                label="Create new artists"
              />
              {useCustomArtists ? (
                <TextField
                  label="New artist names"
                  value={customArtistsText}
                  onChange={(event) => setCustomArtistsText(event.target.value)}
                  placeholder="Antônio Carlos Jobim, Chico Buarque"
                  helperText="Separate multiple artists with commas."
                  fullWidth
                />
              ) : null}
            </Stack>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button
            onClick={() => setIsEditSongDialogOpen(false)}
            disabled={isSavingSongMetadata}
            sx={{ color: "#6b6257" }}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleSaveSongMetadata}
            disabled={isSavingSongMetadata}
            sx={{
              bgcolor: "#14532d",
              borderRadius: 999,
              fontWeight: 800,
              "&:hover": { bgcolor: "#0f3f22" },
            }}
          >
            {isSavingSongMetadata ? "Saving..." : "Save"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={isPlaylistDialogOpen}
        onClose={() => setIsPlaylistDialogOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Add Song to Playlist</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ pt: 1 }}>
            <Stack spacing={1}>
              <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
                Your playlists
              </Typography>
              {availablePlaylists.length ? (
                availablePlaylists.map((playlist) => {
                  const alreadyAdded = song
                    ? playlist.songs.some((songId) => songVersionIds.includes(songId))
                    : false;

                  return (
                    <Stack
                      key={playlist.id}
                      direction="row"
                      alignItems="center"
                      justifyContent="space-between"
                      spacing={2}
                      sx={{
                        border: "1px solid rgba(87, 83, 78, 0.14)",
                        borderRadius: 2,
                        px: 2,
                        py: 1.5,
                      }}
                    >
                      <Stack spacing={0.25}>
                        <Typography sx={{ fontWeight: 700 }}>{playlist.name}</Typography>
                        <Typography color="text.secondary" sx={{ fontSize: 14 }}>
                          {playlist.is_liked_songs
                            ? "Your default liked songs playlist"
                            : `${playlist.songs.length} songs`}
                        </Typography>
                      </Stack>
                      <Button
                        variant={alreadyAdded ? "contained" : "outlined"}
                        disabled={alreadyAdded || activePlaylistId === playlist.id}
                        onClick={() => handleAddToExistingPlaylist(playlist)}
                        sx={{
                          minWidth: 112,
                          borderRadius: 999,
                          fontWeight: 800,
                          borderColor: "rgba(20, 83, 45, 0.28)",
                          color: alreadyAdded ? "#fffaf3" : "#14532d",
                          bgcolor: alreadyAdded ? "#14532d" : "transparent",
                        }}
                      >
                        {alreadyAdded
                          ? "Added"
                          : activePlaylistId === playlist.id
                            ? "Saving..."
                            : "Add"}
                      </Button>
                    </Stack>
                  );
                })
              ) : (
                <Typography color="text.secondary">
                  You do not have any playlists yet.
                </Typography>
              )}
            </Stack>

            <Stack spacing={1.25}>
              <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
                Create a new playlist
              </Typography>
              <TextField
                label="Playlist name"
                value={newPlaylistName}
                onChange={(event) => setNewPlaylistName(event.target.value)}
                placeholder="Late Night Sambas"
                fullWidth
              />
            </Stack>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button onClick={() => setIsPlaylistDialogOpen(false)} sx={{ color: "#6b6257" }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleCreatePlaylist}
            disabled={isCreatingPlaylist}
            sx={{
              bgcolor: "#14532d",
              borderRadius: 999,
              fontWeight: 800,
              "&:hover": { bgcolor: "#0f3f22" },
            }}
          >
            {isCreatingPlaylist ? "Creating..." : "Create Playlist"}
          </Button>
        </DialogActions>
      </Dialog>
      <ProfileMenu
        currentUser={currentUser}
        onLogout={onLogout}
        anchorEl={profileMenuAnchor}
        onClose={() => setProfileMenuAnchor(null)}
      />
    </Box>
  );
}
