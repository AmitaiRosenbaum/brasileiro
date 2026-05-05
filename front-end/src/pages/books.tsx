import {
  Box,
  Container,
  ImageList,
  ImageListItem,
  ImageListItemBar,
  Link,
  Skeleton,
  Stack,
  Typography,
} from "@mui/material";
import type { AuthenticatedUser } from "../api/auth";
import { useBooks } from "../api/hooks/songs";
import AppBrand from "../components/AppBrand";
import ProfileMenu, { ProfileAvatarButton } from "../components/ProfileMenu";
import { useState } from "react";
import { navigateTo, navigateToBook } from "../utils/navigation";

type BooksPageProps = {
  currentUser: AuthenticatedUser | null;
  onLogout: () => void;
};

export default function BooksPage({ currentUser, onLogout }: BooksPageProps) {
  const { data: books, isLoading } = useBooks();
  const [profileMenuAnchor, setProfileMenuAnchor] = useState<HTMLElement | null>(null);

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
              <Typography variant="h2">Books</Typography>
              <Typography color="text.secondary">
                {books.length ? `${books.length} books` : "Loading books"}
              </Typography>
            </Stack>
            <Stack direction="row" alignItems="center" spacing={2}>
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

          {isLoading ? (
            <ImageList cols={4} gap={18} sx={{ m: 0 }}>
              {[...Array(8)].map((_item, index) => (
                <ImageListItem key={index}>
                  <Skeleton variant="rectangular" sx={{ aspectRatio: "3 / 4" }} />
                  <Skeleton height={34} />
                </ImageListItem>
              ))}
            </ImageList>
          ) : (
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "repeat(2, minmax(0, 1fr))",
                  sm: "repeat(3, minmax(0, 1fr))",
                  md: "repeat(4, minmax(0, 1fr))",
                },
                gap: { xs: 2, md: 3 },
              }}
            >
              {books.map((book) => (
                <Box
                  key={book.id}
                  component="button"
                  type="button"
                  onClick={() => navigateToBook(book.id)}
                  sx={{
                    display: "block",
                    p: 0,
                    border: 0,
                    bgcolor: "transparent",
                    cursor: "pointer",
                    textAlign: "left",
                  }}
                >
                  <ImageListItem
                    sx={{
                      overflow: "hidden",
                      borderRadius: 2,
                      border: "1px solid rgba(87, 83, 78, 0.16)",
                      bgcolor: "#fffaf3",
                      boxShadow: "0 14px 34px rgba(28, 25, 23, 0.10)",
                    }}
                  >
                    {book.cover_image ? (
                      <Box
                        component="img"
                        src={book.cover_image}
                        alt=""
                        loading="lazy"
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
                          p: 2,
                          bgcolor: "#17351f",
                          color: "#fffaf3",
                        }}
                      >
                        <Typography variant="h5" sx={{ fontWeight: 850 }}>
                          {book.title}
                        </Typography>
                      </Stack>
                    )}
                    <ImageListItemBar
                      title={book.title}
                      sx={{
                        "& .MuiImageListItemBar-title": {
                          fontWeight: 800,
                          whiteSpace: "normal",
                          lineHeight: 1.2,
                        },
                      }}
                    />
                  </ImageListItem>
                </Box>
              ))}
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
    </Box>
  );
}
