import { Box, Stack, Typography } from "@mui/material";
import SongInputComponent from "../sections/SongInput";
import SongSuggestionSlider from "../sections/SongSuggestion";
import { useAllSongs } from "../api/hooks/songs";
import SongContext from "../contexts/SongContext";
import Footer from "../sections/Footer";

export default function MainPage() {
  const { data: songs, isLoading } = useAllSongs();

  return (
    <>
      <Box sx={{ pl: 30, pr: 30 }}>
        <Stack spacing={2} direction="column">
          <SongContext value={{ data: songs, isLoading }}>
            <Typography variant="h2">Brasileiro</Typography>
            <SongInputComponent />
            <Typography variant="h4">Suggestions for you</Typography>
            <SongSuggestionSlider />
            <Box sx={{ pt: 10 }}>
              <Footer />
            </Box>
          </SongContext>
        </Stack>
      </Box>
    </>
  );
}
