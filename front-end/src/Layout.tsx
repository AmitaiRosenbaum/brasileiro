import type React from "react";
import { Box } from "@mui/material";

export default function Layout({ children }: { children: React.ReactElement }) {
  return (
    <Box
      sx={{
        width: "100%",
        minHeight: "100vh",
        bgcolor: "#f7f3ed",
        color: "#1c1917",
      }}
    >
      {children}
    </Box>
  );
}
