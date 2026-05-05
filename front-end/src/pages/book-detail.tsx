import {
  Alert,
  Box,
  Container,
  Divider,
  Fab,
  Link,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Skeleton,
  Stack,
  SvgIcon,
  Typography,
  Zoom,
} from "@mui/material";
import { useEffect, useState } from "react";
import type { AuthenticatedUser } from "../api/auth";
import { useBooks, useBookSongs } from "../api/hooks/songs";
import AppBrand from "../components/AppBrand";
import ProfileMenu, { ProfileAvatarButton } from "../components/ProfileMenu";
import { navigateTo, navigateToSong } from "../utils/navigation";

type BookDetailPageProps = {
  currentUser: AuthenticatedUser | null;
  onLogout: () => void;
  search: string;
};

function ArrowUpIcon() {
  return (
    <SvgIcon aria-hidden="true" viewBox="0 0 24 24">
      <path
        d="M12 19V5m0 0-7 7m7-7 7 7"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
    </SvgIcon>
  );
}

function ArrowLeftIcon() {
  return (
    <SvgIcon aria-hidden="true" viewBox="0 0 24 24">
      <path
        d="M19 12H5m0 0 7-7m-7 7 7 7"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
    </SvgIcon>
  );
}

export default function BookDetailPage({
  currentUser,
  onLogout,
  search,
}: BookDetailPageProps) {
  const bookId = Number(new URLSearchParams(search).get("id"));
  const { book, data: songs, isLoading } = useBookSongs(bookId || null);
  const { data: cachedBooks } = useBooks();
  const cachedBook = cachedBooks.find((candidate) => candidate.id === bookId);
  const displayBook = cachedBook ?? book;
  const [profileMenuAnchor, setProfileMenuAnchor] = useState<HTMLElement | null>(null);
  const [showScrollTop, setShowScrollTop] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setShowScrollTop(window.scrollY > 420);
    };

    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const handleScrollTop = () => {
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
              <Link
                component="button"
                type="button"
                underline="none"
                onClick={() => navigateTo("/books")}
                sx={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 0.75,
                  border: 0,
                  bgcolor: "transparent",
                  color: "#14532d",
                  cursor: "pointer",
                  fontWeight: 800,
                  p: 0,
                }}
              >
                <ArrowLeftIcon />
                Books
              </Link>
              <AppBrand />
            </Stack>
            <Stack direction="row" alignItems="center" spacing={2}>
              <ProfileAvatarButton
                currentUser={currentUser}
                onClick={(event) => setProfileMenuAnchor(event.currentTarget)}
              />
            </Stack>
          </Stack>

          {!bookId ? (
            <Alert severity="warning">We couldn't find that book.</Alert>
          ) : isLoading ? (
            <Stack spacing={2}>
              <Skeleton height={78} width="60%" />
              {[...Array(10)].map((_item, index) => (
                <Skeleton key={index} height={58} />
              ))}
            </Stack>
          ) : !displayBook ? (
            <Alert severity="warning">We couldn't find that book.</Alert>
          ) : (
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", md: "260px minmax(0, 1fr)" },
                gap: { xs: 3, md: 4 },
                alignItems: "start",
              }}
            >
              <Box
                sx={{
                  overflow: "hidden",
                  borderRadius: 2,
                  border: "1px solid rgba(87, 83, 78, 0.16)",
                  bgcolor: "#fffaf3",
                  boxShadow: "0 14px 34px rgba(28, 25, 23, 0.10)",
                }}
              >
                {displayBook.cover_image ? (
                  <Box
                    component="img"
                    src={displayBook.cover_image}
                    alt=""
                    sx={{
                      width: "100%",
                      aspectRatio: "3 / 4",
                      objectFit: "cover",
                      display: "block",
                    }}
                  />
                ) : (
                  <Stack
                    justifyContent="center"
                    sx={{
                      aspectRatio: "3 / 4",
                      p: 3,
                      bgcolor: "#17351f",
                      color: "#fffaf3",
                    }}
                  >
                    <Typography variant="h4" sx={{ fontWeight: 850 }}>
                      {displayBook.title}
                    </Typography>
                  </Stack>
                )}
              </Box>

              <Stack spacing={2}>
                <Stack spacing={0.75}>
                  <Typography variant="h2">{displayBook.title}</Typography>
                  <Typography color="text.secondary">
                    {songs.length} {songs.length === 1 ? "song" : "songs"}
                  </Typography>
                </Stack>
                <Divider />
                <List disablePadding>
                  {songs.map((song) => (
                    <ListItem key={song.id} disableGutters divider>
                      <ListItemButton onClick={() => navigateToSong(song.id, song.id)}>
                        <ListItemText
                          primary={`${song.book_song_index ?? ""}. ${song.title}`}
                          secondary={
                            song.artists.length
                              ? song.artists.join(", ")
                              : "Unknown artist"
                          }
                          slotProps={{
                            primary: { variant: "body1" },
                            secondary: { color: "text.secondary" },
                          }}
                        />
                      </ListItemButton>
                    </ListItem>
                  ))}
                </List>
              </Stack>
            </Box>
          )}
        </Stack>
      </Container>
      <ProfileMenu
        currentUser={currentUser}
        onLogout={onLogout}
        anchorEl={profileMenuAnchor}
        onClose={() => setProfileMenuAnchor(null)}
      />
      <Zoom in={showScrollTop}>
        <Fab
          color="primary"
          size="medium"
          aria-label="Scroll to top"
          onClick={handleScrollTop}
          sx={{
            position: "fixed",
            right: { xs: 18, sm: 28 },
            bottom: { xs: 18, sm: 28 },
            bgcolor: "#14532d",
            color: "#fffaf3",
            boxShadow: "0 14px 34px rgba(20, 83, 45, 0.28)",
            "&:hover": { bgcolor: "#0f3f22" },
          }}
        >
          <ArrowUpIcon />
        </Fab>
      </Zoom>
    </Box>
  );
}
