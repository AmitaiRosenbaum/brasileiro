import {
  Box,
  Button,
  Container,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import type { AuthenticatedUser } from "../api/auth";
import AppBrand from "../components/AppBrand";
import ProfileMenu, { ProfileAvatarButton } from "../components/ProfileMenu";
import Footer from "../sections/Footer";
import { navigateTo } from "../utils/navigation";
import { useState } from "react";

type AcknowledgmentsPageProps = {
  currentUser: AuthenticatedUser | null;
  onLogout: () => void;
};

export default function AcknowledgmentsPage({
  currentUser,
  onLogout,
}: AcknowledgmentsPageProps) {
  const [profileMenuAnchor, setProfileMenuAnchor] =
    useState<HTMLElement | null>(null);
  const acknowledgmentName =
    import.meta.env.VITE_ACKNOWLEDGMENT_NAME || "our human reviewer";

  return (
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
            <ProfileAvatarButton
              currentUser={currentUser}
              onClick={(event) => setProfileMenuAnchor(event.currentTarget)}
            />
          </Stack>

          <Paper
            elevation={0}
            sx={{
              p: { xs: 2.5, sm: 3 },
              borderRadius: 2,
              border: "1px solid rgba(87, 83, 78, 0.14)",
              bgcolor: "rgba(255, 255, 255, 0.86)",
              boxShadow: "0 16px 48px rgba(28, 25, 23, 0.08)",
              maxWidth: 640,
            }}
          >
            <Stack spacing={2}>
              <Typography
                variant="h5"
                sx={{
                  fontWeight: 800,
                  fontSize: { xs: "1.4rem", sm: "1.6rem" },
                }}
              >
                Acknowledgments
              </Typography>
              <Typography
                color="text.secondary"
                sx={{ fontSize: 15, lineHeight: 1.7 }}
              >
                Thank you to {acknowledgmentName} for the outstanding
                human-verification of the classifications from the PDF
                processing engine.
              </Typography>
              <Box>
                <Button
                  variant="contained"
                  onClick={() => navigateTo("/")}
                  sx={{
                    bgcolor: "#14532d",
                    borderRadius: 999,
                    fontWeight: 800,
                    "&:hover": { bgcolor: "#0f3f22" },
                  }}
                >
                  Back Home
                </Button>
              </Box>
            </Stack>
          </Paper>

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
  );
}
