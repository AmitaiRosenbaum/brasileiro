import type React from "react";
import { Box, Grid } from "@mui/material";

export default function Layout({ children }: { children: React.ReactElement }) {
  return (
    <Box sx={{ width: "100vw", height: "100vh" }}>
      <Grid
        container
        spacing={2}
        justifyContent="center"
        alignItems="center"
        sx={{ border: 2, width: "100%", height: "100vh" }}
      >
        {children}
      </Grid>
    </Box>
  );
}
