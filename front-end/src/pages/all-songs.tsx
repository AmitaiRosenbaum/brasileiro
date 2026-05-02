import {
  Box,
  Button,
  ButtonGroup,
  Chip,
  Container,
  Divider,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Skeleton,
  Stack,
  Typography,
} from "@mui/material";
import { useMemo, useRef, useState } from "react";
import type { AuthenticatedUser } from "../api/auth";
import { useAllSongs } from "../api/hooks/songs";
import AppBrand from "../components/AppBrand";
import ProfileMenu, { ProfileAvatarButton } from "../components/ProfileMenu";
import type { SongType } from "../types/songs";
import { navigateToSong } from "../utils/navigation";

function getArtists(song: SongType) {
  return song.artists.length ? song.artists.join(", ") : "Unknown artist";
}

function normalizeIndexText(value: string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function getNormalizedSortValue(value: string) {
  return normalizeIndexText(value).trim().replace(/^[^A-Za-z0-9]+/, "");
}

function getSortableTitle(song: SongType) {
  return getNormalizedSortValue(song.title);
}

function getSongGroup(song: SongType) {
  const normalizedTitle = getSortableTitle(song);
  return getIndexLetter(normalizedTitle);
}

function getArtistGroupName(artist: string) {
  return artist.trim() || "Unknown artist";
}

function getIndexLetter(value: string) {
  const normalizedValue = getNormalizedSortValue(value);
  const firstLetter = normalizedValue.match(/[A-Za-z]/)?.[0]?.toUpperCase();
  return firstLetter ?? "#";
}

function getSongGroupsByTitle(songs: SongType[]) {
  const sortedSongs = [...songs].sort((first, second) =>
    getSortableTitle(first).localeCompare(getSortableTitle(second), undefined, {
      sensitivity: "base",
    }),
  );

  return sortedSongs.reduce<Record<string, SongType[]>>((groups, song) => {
    const group = getSongGroup(song);
    groups[group] = [...(groups[group] ?? []), song];
    return groups;
  }, {});
}

function getSongGroupsByArtist(songs: SongType[]) {
  const groups = songs.reduce<Record<string, SongType[]>>((result, song) => {
    const artistNames = song.artists.length ? song.artists : ["Unknown artist"];

    artistNames.forEach((artist) => {
      const group = getArtistGroupName(artist);
      result[group] = [...(result[group] ?? []), song];
    });

    return result;
  }, {});

  return Object.fromEntries(
    Object.entries(groups)
      .sort(([firstArtist], [secondArtist]) =>
        firstArtist.localeCompare(secondArtist, undefined, { sensitivity: "base" }),
      )
      .map(([artist, artistSongs]) => [
        artist,
        [...artistSongs].sort((first, second) =>
          getSortableTitle(first).localeCompare(getSortableTitle(second), undefined, {
            sensitivity: "base",
          }),
        ),
      ]),
  );
}

type AllSongsPageProps = {
  currentUser: AuthenticatedUser | null;
  onLogout: () => void;
};

export default function AllSongsPage({ currentUser, onLogout }: AllSongsPageProps) {
  const { data: songs, isLoading } = useAllSongs();
  const [sortMode, setSortMode] = useState<"title" | "artist">("title");
  const [profileMenuAnchor, setProfileMenuAnchor] = useState<HTMLElement | null>(null);
  const navigationRef = useRef<HTMLDivElement | null>(null);

  const groupedSongs = useMemo(() => {
    const allSongs = songs ?? [];
    return sortMode === "artist"
      ? getSongGroupsByArtist(allSongs)
      : getSongGroupsByTitle(allSongs);
  }, [songs, sortMode]);

  const navigationTargets = useMemo(() => {
    const entries = Object.keys(groupedSongs);

    if (sortMode === "title") {
      return entries.reduce<Record<string, string>>((result, groupName) => {
        result[groupName] = groupName;
        return result;
      }, {});
    }

    return entries.reduce<Record<string, string>>((result, groupName) => {
      const letter = getIndexLetter(groupName);

      if (!(letter in result)) {
        result[letter] = groupName;
      }

      return result;
    }, {});
  }, [groupedSongs, sortMode]);

  const navigationItems = useMemo(
    () => ["#", ...Array.from({ length: 26 }, (_item, index) => String.fromCharCode(65 + index))],
    [],
  );

  const handleSongClick = (song: SongType) => {
    navigateToSong(song.id);
  };

  const handleSectionJump = (sectionName: string) => {
    const targetId = `song-group-${sectionName}`;
    const target = document.getElementById(targetId);

    if (!target) {
      return;
    }

    const navigationHeight = navigationRef.current?.offsetHeight ?? 0;
    const targetTop = target.getBoundingClientRect().top + window.scrollY;
    const finalTop = Math.max(targetTop - navigationHeight - 28, 0);
    const startTop = window.scrollY;
    const distance = finalTop - startTop;
    const duration = 180;
    const startTime = performance.now();

    const animateScroll = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easedProgress = 1 - (1 - progress) * (1 - progress);

      window.scrollTo({
        top: startTop + distance * easedProgress,
        behavior: "auto",
      });

      if (progress < 1) {
        window.requestAnimationFrame(animateScroll);
      }
    };

    window.requestAnimationFrame(animateScroll);
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
            <Stack spacing={1}>
              <AppBrand />
              <Typography variant="h2">All Songs A-Z</Typography>
              <Typography color="text.secondary">
                {songs ? `${songs.length} songs` : "Loading songs"}
              </Typography>
            </Stack>
            <ProfileAvatarButton
              currentUser={currentUser}
              onClick={(event) => setProfileMenuAnchor(event.currentTarget)}
            />
          </Stack>

          <Box sx={{ maxWidth: 900 }}>
            <Stack spacing={3}>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                alignItems={{ xs: "flex-start", sm: "center" }}
                justifyContent="space-between"
                spacing={1.5}
              >
                <Typography color="text.secondary">
                  Browse by song title or by artist.
                </Typography>
                <ButtonGroup
                  variant="outlined"
                  size="small"
                  aria-label="Sort all songs"
                  sx={{
                    "& .MuiButton-root": {
                      borderColor: "rgba(20, 83, 45, 0.28)",
                      color: "#14532d",
                      fontWeight: 700,
                    },
                    "& .MuiButton-contained": {
                      color: "#fffaf3",
                    },
                  }}
                >
                  <Button
                    variant={sortMode === "title" ? "contained" : "outlined"}
                    onClick={() => setSortMode("title")}
                    sx={
                      sortMode === "title"
                        ? {
                            bgcolor: "#14532d",
                            "&:hover": { bgcolor: "#0f3f22" },
                          }
                        : undefined
                    }
                  >
                    By Title
                  </Button>
                  <Button
                    variant={sortMode === "artist" ? "contained" : "outlined"}
                    onClick={() => setSortMode("artist")}
                    sx={
                      sortMode === "artist"
                        ? {
                            bgcolor: "#14532d",
                            "&:hover": { bgcolor: "#0f3f22" },
                          }
                        : undefined
                    }
                  >
                    By Artist
                  </Button>
                </ButtonGroup>
              </Stack>

              {isLoading ? (
                <Stack spacing={1.5}>
                  {[...Array(12)].map((_item, index) => (
                    <Skeleton key={index} height={56} />
                  ))}
                </Stack>
              ) : (
                <Stack spacing={4}>
                  <Box
                    ref={navigationRef}
                    sx={{
                      position: "sticky",
                      top: 12,
                      zIndex: 1,
                      py: 1,
                      px: 1.25,
                      borderRadius: 3,
                      border: "1px solid rgba(87, 83, 78, 0.12)",
                      bgcolor: "rgba(255, 255, 255, 0.88)",
                      backdropFilter: "blur(10px)",
                      boxShadow: "0 12px 28px rgba(28, 25, 23, 0.08)",
                    }}
                  >
                    <Stack spacing={1}>
                      <Typography
                        variant="caption"
                        sx={{ color: "text.secondary", fontWeight: 700 }}
                      >
                        Jump to section
                      </Typography>
                      <Box
                        sx={{
                          display: "grid",
                          gridTemplateColumns: "repeat(auto-fit, minmax(42px, 1fr))",
                          gap: 0.75,
                        }}
                      >
                        {navigationItems.map((item) => {
                          const targetSection = navigationTargets[item];

                          return (
                            <Chip
                              key={item}
                              label={item}
                              clickable={Boolean(targetSection)}
                              disabled={!targetSection}
                              onClick={
                                targetSection
                                  ? () => handleSectionJump(targetSection)
                                  : undefined
                              }
                              sx={{
                                justifyContent: "center",
                                fontWeight: 800,
                                color: targetSection
                                  ? "#14532d"
                                  : "rgba(28, 25, 23, 0.35)",
                                bgcolor: targetSection
                                  ? "rgba(20, 83, 45, 0.08)"
                                  : "rgba(28, 25, 23, 0.05)",
                                border: "1px solid",
                                borderColor: targetSection
                                  ? "rgba(20, 83, 45, 0.16)"
                                  : "rgba(28, 25, 23, 0.08)",
                                "&:hover": targetSection
                                  ? { bgcolor: "rgba(20, 83, 45, 0.16)" }
                                  : undefined,
                              }}
                            />
                          );
                        })}
                      </Box>
                    </Stack>
                  </Box>

                  {Object.entries(groupedSongs).map(
                    ([letter, groupedSongsForLetter]) => (
                      <Box key={letter} id={`song-group-${letter}`}>
                        <Typography variant="h5" sx={{ mb: 1 }}>
                          {letter}
                        </Typography>
                        <Divider />
                        <List disablePadding>
                          {groupedSongsForLetter.map((song) => (
                            <ListItem key={song.id} disableGutters divider>
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
                    ),
                  )}
                </Stack>
              )}
            </Stack>
          </Box>
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
