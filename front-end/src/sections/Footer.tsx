import {
  Box,
  IconButton,
  Link,
  Stack,
  SvgIcon,
  Typography,
} from "@mui/material";
import type React from "react";
import { navigateTo } from "../utils/navigation";

function GitHubIcon() {
  return (
    <SvgIcon aria-hidden="true" viewBox="0 0 24 24">
      <path d="M12 2C6.48 2 2 6.58 2 12.25c0 4.52 2.87 8.36 6.84 9.72.5.1.68-.22.68-.49 0-.24-.01-1.05-.01-1.91-2.78.62-3.37-1.22-3.37-1.22-.45-1.19-1.11-1.51-1.11-1.51-.91-.64.07-.63.07-.63 1 .07 1.53 1.06 1.53 1.06.9 1.57 2.36 1.12 2.94.86.09-.67.35-1.12.64-1.38-2.22-.26-4.56-1.14-4.56-5.07 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.31.1-2.71 0 0 .84-.28 2.75 1.05A9.35 9.35 0 0 1 12 6.93c.85 0 1.7.12 2.5.35 1.91-1.33 2.75-1.05 2.75-1.05.55 1.4.2 2.45.1 2.71.64.72 1.03 1.63 1.03 2.75 0 3.94-2.34 4.81-4.57 5.06.36.32.68.94.68 1.9 0 1.37-.01 2.48-.01 2.82 0 .27.18.59.69.49A10.13 10.13 0 0 0 22 12.25C22 6.58 17.52 2 12 2Z" />
    </SvgIcon>
  );
}

export default function Footer() {
  const handleSongsClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    navigateTo("/songs");
  };

  const handleAcknowledgmentsClick = (
    event: React.MouseEvent<HTMLAnchorElement>,
  ) => {
    event.preventDefault();
    navigateTo("/acknowledgments");
  };

  return (
    <Box
      component="footer"
      sx={{
        display: "flex",
        justifyContent: "space-between",
        gap: 2,
        flexWrap: "wrap",
        pt: 2,
        pb: 1,
        color: "text.secondary",
      }}
    >
      <Typography>Brasileiro sheet music archive</Typography>
      <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap">
        <Link
          color="#14532d"
          underline="hover"
          href="/songs"
          onClick={handleSongsClick}
          sx={{ fontWeight: 700 }}
        >
          All Songs A-Z
        </Link>
        <Link
          color="#14532d"
          underline="hover"
          href="/acknowledgments"
          onClick={handleAcknowledgmentsClick}
          sx={{ fontWeight: 700 }}
        >
          Acknowledgments
        </Link>
        <IconButton
          component="a"
          href="https://github.com/AmitaiRosenbaum/brasileiro"
          target="_blank"
          rel="noreferrer"
          aria-label="GitHub repository"
          size="small"
          sx={{ color: "#14532d" }}
        >
          <GitHubIcon />
        </IconButton>
      </Stack>
    </Box>
  );
}
