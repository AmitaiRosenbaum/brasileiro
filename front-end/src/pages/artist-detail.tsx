import {
  Alert,
  Box,
  Container,
  Divider,
  Link,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Skeleton,
  Stack,
  SvgIcon,
  Typography,
} from "@mui/material";
import { useState } from "react";
import type { AuthenticatedUser } from "../api/auth";
import { useArtistSongs } from "../api/hooks/songs";
import AppBrand from "../components/AppBrand";
import ProfileMenu, { ProfileAvatarButton } from "../components/ProfileMenu";
import {
  handleInternalLinkClick,
  navigateTo,
  songPath,
} from "../utils/navigation";

type ArtistDetailPageProps = {
  currentUser: AuthenticatedUser | null;
  onLogout: () => void;
  search: string;
};

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

export default function ArtistDetailPage({
  currentUser,
  onLogout,
  search,
}: ArtistDetailPageProps) {
  const artistName = new URLSearchParams(search).get("name")?.trim() || null;
  const { artist, data: songs, isLoading, error } = useArtistSongs(artistName);
  const [profileMenuAnchor, setProfileMenuAnchor] =
    useState<HTMLElement | null>(null);

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
                onClick={() => navigateTo("/songs")}
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
                  width: "fit-content",
                }}
              >
                <Box sx={{ display: "inline-flex", fontSize: 18 }}>
                  <ArrowLeftIcon />
                </Box>
                All Songs A–Z
              </Link>
              <AppBrand compact />
            </Stack>
            <ProfileAvatarButton
              currentUser={currentUser}
              onClick={(event) => setProfileMenuAnchor(event.currentTarget)}
            />
          </Stack>

          {!artistName ? (
            <Alert severity="warning">We couldn't find that artist.</Alert>
          ) : isLoading ? (
            <Stack spacing={1.5} sx={{ maxWidth: 900 }}>
              <Skeleton height={72} />
              {[...Array(8)].map((_item, index) => (
                <Skeleton key={index} height={56} />
              ))}
            </Stack>
          ) : error || !artist ? (
            <Alert severity="warning">We couldn't find that artist.</Alert>
          ) : (
            <Stack spacing={2} sx={{ maxWidth: 900 }}>
              <Stack spacing={0.75}>
                <Typography
                  variant="overline"
                  sx={{ color: "#14532d", fontWeight: 800 }}
                >
                  Artist
                </Typography>
                <Typography variant="h2">{artist.name}</Typography>
                <Typography color="text.secondary">
                  {songs.length} {songs.length === 1 ? "song" : "songs"}
                </Typography>
              </Stack>
              <Divider />
              <List disablePadding>
                {songs.map((song) => {
                  const href = songPath(song.id);
                  const versionLabel =
                    song.versions.length > 1
                      ? `${song.versions.length} versions`
                      : "1 version";
                  return (
                    <ListItem key={song.id} disableGutters divider>
                      <ListItemButton
                        component="a"
                        href={href}
                        onClick={(event) =>
                          handleInternalLinkClick(event, href)
                        }
                      >
                        <ListItemText
                          primary={song.title}
                          secondary={`${song.artists.join(", ")} · ${versionLabel}`}
                          slotProps={{
                            primary: { variant: "body1" },
                            secondary: { color: "text.secondary" },
                          }}
                        />
                      </ListItemButton>
                    </ListItem>
                  );
                })}
              </List>
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
