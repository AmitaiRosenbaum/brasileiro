import {
  Box,
  Container,
  Divider,
  Link,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { useState } from "react";
import SongInputComponent from "../sections/SongInput";
import SongSuggestionSlider from "../sections/SongSuggestion";
import { useAllSongs, useArtists } from "../api/hooks/songs";
import SongContext from "../contexts/SongContext";
import Footer from "../sections/Footer";
import { navigateTo } from "../utils/navigation";
import type { AuthenticatedUser } from "../api/auth";
import AppBrand from "../components/AppBrand";
import ProfileMenu, { ProfileAvatarButton } from "../components/ProfileMenu";

type MainPageProps = {
  currentUser: AuthenticatedUser | null;
  onLogout: () => void;
};

export default function MainPage({ currentUser, onLogout }: MainPageProps) {
  const { pagination } = useAllSongs({ page_size: 12 });
  const { data: suggestedSongs, isLoading: areSuggestionsLoading } = useAllSongs(
    {
      page_size: 8,
      random: true,
    },
    true,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    },
  );
  const { data: artists } = useArtists();
  const [profileMenuAnchor, setProfileMenuAnchor] =
    useState<HTMLElement | null>(null);

  return (
    <SongContext value={{ data: suggestedSongs, isLoading: areSuggestionsLoading }}>
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
                  component="button"
                  type="button"
                  underline="none"
                  onClick={() => navigateTo("/songs")}
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
                      {pagination?.total ?? "--"}
                    </Typography>
                    <Typography sx={{ color: "rgba(255, 250, 243, 0.76)" }}>
                      searchable scores in the current collection.
                    </Typography>
                  </Stack>
                  <Divider sx={{ borderColor: "rgba(255, 250, 243, 0.18)" }} />
                  <Stack direction="row" spacing={4}>
                    <Box>
                      <Typography variant="h5" sx={{ fontWeight: 800 }}>
                        {artists.length || "--"}
                      </Typography>
                      <Typography sx={{ color: "rgba(255, 250, 243, 0.68)" }}>
                        artists
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="h5" sx={{ fontWeight: 800 }}>
                        A-Z
                      </Typography>
                      <Typography sx={{ color: "rgba(255, 250, 243, 0.68)" }}>
                        browsing
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
                    Suggestions for you
                  </Typography>
                  <Typography color="text.secondary">
                    A quick shuffle from the archive.
                  </Typography>
                </Box>
              </Stack>
              <SongSuggestionSlider />
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
      </Box>
    </SongContext>
  );
}
