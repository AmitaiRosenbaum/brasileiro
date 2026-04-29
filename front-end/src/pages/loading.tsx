import { Box, CircularProgress, Stack, Typography } from "@mui/material";

export default function LoadingPage() {
  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        px: 3,
        background:
          "radial-gradient(circle at top, rgba(20, 83, 45, 0.14), transparent 32%), linear-gradient(145deg, #f7f3ed 0%, #eef4ee 46%, #f8efe7 100%)",
      }}
    >
      <Stack spacing={2} alignItems="center">
        <CircularProgress size={34} sx={{ color: "#14532d" }} />
        <Typography variant="h6" sx={{ fontWeight: 700 }}>
          Checking your session
        </Typography>
        <Typography color="text.secondary">
          Please wait while Brasileiro opens the right page.
        </Typography>
      </Stack>
    </Box>
  );
}
