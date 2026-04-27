import { Box, Link, Typography } from "@mui/material";
import type React from "react";
import { navigateTo } from "../utils/navigation";

export default function Footer() {
  const handleClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    navigateTo("/songs");
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
      <Link
        color="#14532d"
        underline="hover"
        href="/songs"
        onClick={handleClick}
        sx={{ fontWeight: 700 }}
      >
        All Songs A-Z
      </Link>
    </Box>
  );
}
