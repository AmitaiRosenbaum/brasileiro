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
  Pagination,
  Skeleton,
  Stack,
  Typography,
} from "@mui/material";
import { useEffect, useMemo, useState } from "react";
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
  const [sortMode, setSortMode] = useState<"title" | "artist">("title");
  const [page, setPage] = useState(1);
  const [activeSection, setActiveSection] = useState("A");
  const { data: songs, isLoading, pagination } = useAllSongs({
    mode: sortMode,
    page,
    page_size: 50,
    section: activeSection,
  });
  const [profileMenuAnchor, setProfileMenuAnchor] = useState<HTMLElement | null>(null);

  const groupedSongs = useMemo(() => {
    const allSongs = songs ?? [];
    return sortMode === "artist"
      ? getSongGroupsByArtist(allSongs)
      : getSongGroupsByTitle(allSongs);
  }, [songs, sortMode]);

  const availableSections = useMemo(
    () => new Set(pagination?.sections ?? []),
    [pagination?.sections],
  );

  const navigationItems = useMemo(
    () => ["#", ...Array.from({ length: 26 }, (_item, index) => String.fromCharCode(65 + index))],
    [],
  );

  useEffect(() => {
    const sections = pagination?.sections ?? [];
    if (sections.length && !sections.includes(activeSection)) {
      setActiveSection(sections[0]);
      setPage(1);
    }
  }, [activeSection, pagination?.sections]);

  const handleSongClick = (song: SongType) => {
    navigateToSong(song.id);
  };

  const handleSectionSelect = (sectionName: string) => {
    setActiveSection(sectionName);
    setPage(1);
    window.scrollTo({ top: 0, behavior: "smooth" });
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
                {pagination ? `${pagination.total} songs` : "Loading songs"}
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
                    onClick={() => {
                      setSortMode("title");
                      setPage(1);
                      setActiveSection("A");
                    }}
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
                    onClick={() => {
                      setSortMode("artist");
                      setPage(1);
                      setActiveSection("A");
                    }}
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
                          const isAvailable = availableSections.has(item);
                          const isActive = activeSection === item;

                          return (
                            <Chip
                              key={item}
                              label={item}
                              clickable={isAvailable}
                              disabled={!isAvailable}
                              color={isActive ? "primary" : "default"}
                              onClick={isAvailable ? () => handleSectionSelect(item) : undefined}
                              sx={{
                                justifyContent: "center",
                                fontWeight: 800,
                                color: isActive
                                  ? "#fffaf3"
                                  : isAvailable
                                  ? "#14532d"
                                  : "rgba(28, 25, 23, 0.35)",
                                bgcolor: isActive
                                  ? "#14532d"
                                  : isAvailable
                                  ? "rgba(20, 83, 45, 0.08)"
                                  : "rgba(28, 25, 23, 0.05)",
                                border: "1px solid",
                                borderColor: isAvailable
                                  ? "rgba(20, 83, 45, 0.16)"
                                  : "rgba(28, 25, 23, 0.08)",
                                "&:hover": isAvailable
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
                  {pagination && pagination.total_pages > 1 ? (
                    <Stack alignItems="center" sx={{ pt: 1 }}>
                      <Pagination
                        count={pagination.total_pages}
                        page={pagination.page}
                        onChange={(_event, nextPage) => {
                          setPage(nextPage);
                          window.scrollTo({ top: 0, behavior: "smooth" });
                        }}
                        color="primary"
                      />
                    </Stack>
                  ) : null}
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
