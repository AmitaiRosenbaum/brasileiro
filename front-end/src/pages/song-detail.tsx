import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Container,
  Link,
  Stack,
  Typography,
} from "@mui/material";
import type React from "react";
import type { AuthenticatedUser } from "../api/auth";
import { useAllSongs, useSongUrl } from "../api/hooks/songs";
import { navigateTo } from "../utils/navigation";

type SongDetailPageProps = {
  currentUser: AuthenticatedUser | null;
  onLogout: () => void;
  search: string;
};

const pdfFrameWidth = "min(100%, 920px)";

export default function SongDetailPage({
  currentUser,
  onLogout,
  search,
}: SongDetailPageProps) {
  const { data: songs, isLoading: isSongsLoading } = useAllSongs();
  const songKey = new URLSearchParams(search).get("key");
  const song = songs?.find((item) => item.key === songKey) ?? null;
  const { data: songUrl, isLoading: isPdfLoading } = useSongUrl(song);

  const handleHomeClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    navigateTo("/");
  };

  const handleAllSongsClick = () => {
    navigateTo("/songs");
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background:
          "linear-gradient(145deg, #f7f3ed 0%, #eef4ee 46%, #f8efe7 100%)",
      }}
    >
      <Container maxWidth={false} sx={{ py: { xs: 2, md: 3 }, px: { xs: 2, md: 3 } }}>
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
            </Stack>
            <Stack direction="row" spacing={1.5} useFlexGap flexWrap="wrap">
              {currentUser ? (
                <Typography color="text.secondary" sx={{ alignSelf: "center", fontSize: 14 }}>
                  Signed in as {currentUser.username}
                </Typography>
              ) : null}
              <Button
                variant="outlined"
                onClick={handleAllSongsClick}
                sx={{
                  borderColor: "rgba(20, 83, 45, 0.28)",
                  color: "#14532d",
                  fontWeight: 700,
                  borderRadius: 999,
                }}
              >
                Back to A-Z
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

          {isSongsLoading ? (
            <Stack spacing={2} alignItems="center" sx={{ py: 8 }}>
              <CircularProgress size={34} sx={{ color: "#14532d" }} />
              <Typography color="text.secondary">Loading song details...</Typography>
            </Stack>
          ) : !songKey || song == null ? (
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
              <Stack spacing={1} sx={{ width: pdfFrameWidth }}>
                <Typography
                  variant="h2"
                  sx={{
                    fontWeight: 850,
                    lineHeight: 0.95,
                    fontSize: { xs: "2.4rem", md: "3.8rem" },
                  }}
                >
                  {song.title}
                </Typography>
                <Typography color="text.secondary" sx={{ fontSize: { xs: 17, md: 20 } }}>
                  {song.artists.length ? song.artists.join(", ") : "Unknown artist"}
                </Typography>
              </Stack>

              <Box
                sx={{
                  width: pdfFrameWidth,
                  borderRadius: 3,
                  overflow: "hidden",
                  border: "1px solid rgba(87, 83, 78, 0.14)",
                  bgcolor: "#ffffff",
                  aspectRatio: "8.5 / 11.4",
                  minHeight: { xs: "110vh", md: "auto" },
                }}
              >
                {songUrl ? (
                  <Box
                    component="iframe"
                    src={songUrl}
                    title={`${song.title} PDF`}
                    sx={{
                      width: "100%",
                      height: "100%",
                      border: 0,
                      display: "block",
                    }}
                  />
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
    </Box>
  );
}
