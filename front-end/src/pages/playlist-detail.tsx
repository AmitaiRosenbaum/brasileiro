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
  Typography,
} from "@mui/material";
import type React from "react";
import { useMemo, useState } from "react";
import type { AuthenticatedUser } from "../api/auth";
import ProfileMenu, { ProfileAvatarButton } from "../components/ProfileMenu";
import { useAllSongs } from "../api/hooks/songs";
import { navigateTo, navigateToSong } from "../utils/navigation";

type PlaylistDetailPageProps = {
  currentUser: AuthenticatedUser | null;
  onLogout: () => void;
  search: string;
};

export default function PlaylistDetailPage({
  currentUser,
  onLogout,
  search,
}: PlaylistDetailPageProps) {
  const { data: songs, isLoading } = useAllSongs();
  const [profileMenuAnchor, setProfileMenuAnchor] = useState<HTMLElement | null>(null);
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

  const handleHomeClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    navigateTo("/");
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
                    <ListItem key={song.id} disablePadding divider={index < playlistSongs.length - 1}>
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
