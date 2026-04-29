import {
  Box,
  Button,
  Divider,
  Link,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Skeleton,
  Stack,
  Typography,
} from "@mui/material";
import type React from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { AuthenticatedUser } from "../api/auth";
import { useAllSongs, useSongUrl } from "../api/hooks/songs";
import type { SongType } from "../types/songs";
import { navigateTo } from "../utils/navigation";

function getArtists(song: SongType) {
  return song.artists.length ? song.artists.join(", ") : "Unknown artist";
}

function getSortTitle(song: SongType) {
  return song.title.replace(/^(a|an|the)\s+/i, "");
}

function getSongGroup(song: SongType) {
  const firstLetter = getSortTitle(song).charAt(0).toUpperCase();
  return /^[A-Z]$/.test(firstLetter) ? firstLetter : "#";
}

type AllSongsPageProps = {
  currentUser: AuthenticatedUser | null;
  onLogout: () => void;
};

export default function AllSongsPage({ currentUser, onLogout }: AllSongsPageProps) {
  const { data: songs, isLoading } = useAllSongs();
  const [selectedSong, setSelectedSong] = useState<SongType | null>(null);
  const { data: songUrl } = useSongUrl(selectedSong);
  const opened = useRef(false);

  const groupedSongs = useMemo(() => {
    const sortedSongs = [...(songs ?? [])].sort((first, second) =>
      getSortTitle(first).localeCompare(getSortTitle(second), undefined, {
        sensitivity: "base",
      }),
    );

    return sortedSongs.reduce<Record<string, SongType[]>>((groups, song) => {
      const group = getSongGroup(song);
      groups[group] = [...(groups[group] ?? []), song];
      return groups;
    }, {});
  }, [songs]);

  const handleHomeClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    navigateTo("/");
  };

  const handleSongClick = (song: SongType) => {
    opened.current = false;
    setSelectedSong(song);
  };

  useEffect(() => {
    if (songUrl != null && !opened.current) {
      window.open(songUrl);
      opened.current = true;
    }
  }, [songUrl]);

  return (
    <Box
      sx={{
        maxWidth: 900,
        mx: "auto",
        width: "100%",
        px: { xs: 2, sm: 4 },
        py: { xs: 3, md: 5 },
      }}
    >
      <Stack spacing={3}>
        <Stack spacing={2}>
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
              <Typography variant="h2">All Songs A-Z</Typography>
              <Typography color="text.secondary">
                {songs ? `${songs.length} songs` : "Loading songs"}
              </Typography>
            </Stack>
            <Stack
              direction="row"
              alignItems="center"
              spacing={1.5}
              useFlexGap
              flexWrap="wrap"
            >
              {currentUser ? (
                <Typography color="text.secondary" sx={{ fontSize: 14 }}>
                  Signed in as {currentUser.username}
                </Typography>
              ) : null}
              <Button
                variant="outlined"
                size="small"
                onClick={onLogout}
                sx={{
                  borderColor: "rgba(20, 83, 45, 0.28)",
                  color: "#14532d",
                  fontWeight: 700,
                  borderRadius: 999,
                  px: 1.8,
                }}
              >
                Log out
              </Button>
            </Stack>
          </Stack>
        </Stack>

        {isLoading ? (
          <Stack spacing={1.5}>
            {[...Array(12)].map((_item, index) => (
              <Skeleton key={index} height={56} />
            ))}
          </Stack>
        ) : (
          <Stack spacing={4}>
            {Object.entries(groupedSongs).map(([letter, songs]) => (
              <Box key={letter}>
                <Typography variant="h5" sx={{ mb: 1 }}>
                  {letter}
                </Typography>
                <Divider />
                <List disablePadding>
                  {songs.map((song) => (
                    <ListItem key={song.key} disableGutters divider>
                      <ListItemButton onClick={() => handleSongClick(song)}>
                        <ListItemText
                          primary={song.title}
                          secondary={getArtists(song)}
                          slotProps={{
                            primary: { variant: "body1" },
                            secondary: { color: "text.secondary" },
                          }}
                        />
                      </ListItemButton>
                    </ListItem>
                  ))}
                </List>
              </Box>
            ))}
          </Stack>
        )}
      </Stack>
    </Box>
  );
}
