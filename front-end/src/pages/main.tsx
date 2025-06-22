import { Box, Stack, Typography } from "@mui/material";
import SongInputComponent from "../sections/SongInput";

export default function MainPage() {
  return (
    <Box sx={{ pl: 30, pr: 30 }}>
      <Stack spacing={2} direction="column">
      <Typography variant="h2">Search for songs</Typography>
      <SongInputComponent />
      </Stack>
    </Box>
  );
}
