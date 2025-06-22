import { Box, Typography } from "@mui/material";
import SongInputComponent from "../sections/SongInput";

export default function MainPage() {
  return (
    <Box sx={{ pl: 30, pr: 30 }}>
      <Typography variant="h1">Search for songs</Typography>
      <SongInputComponent />
    </Box>
  );
}
