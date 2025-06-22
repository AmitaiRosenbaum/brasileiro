import {
  Card,
  CardActionArea,
  CardContent,
  Grid,
  Typography,
} from "@mui/material";
import { useContext, useEffect, useMemo } from "react";
import SongContext from "../../contexts/SongContext";
import { shuffle } from "../../utils/shuffle";

const numberOfCards = 8;

export default function SongSuggestionSlider() {
  const { data: songs } = useContext(SongContext);

  const suggestedSongs = useMemo(() => {
    if (!songs) return songs;
    return shuffle(songs).slice(0, numberOfCards);
  }, [songs]);

  return (
    <Grid container spacing={2} alignItems="stretch">
      {suggestedSongs ? (
        suggestedSongs.map((song, index) => (
          <Grid size={3} key={index}>
            <Card sx={{ height: "100%" }}>
              <CardActionArea
                sx={{
                  "&:focus": {
                    outline: "none",
                  },
                  height: "100%",
                }}
              >
                <CardContent>
                  <Typography gutterBottom color="text.secondary">
                    {song.artists.reduce((all, artist) => all + " & " + artist)}
                  </Typography>
                  <Typography variant="h6">{song.title}</Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))
      ) : (
        <></>
      )}
    </Grid>
  );
}
