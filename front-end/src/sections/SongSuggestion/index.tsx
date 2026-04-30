import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  Grid,
  Skeleton,
  Typography,
} from "@mui/material";
import { useContext, useMemo } from "react";
import SongContext from "../../contexts/SongContext";
import { shuffle } from "../../utils/shuffle";
import type { SongType } from "../../types/songs";
import { navigateToSong } from "../../utils/navigation";

const numberOfCards = 8;

function getArtists(song: SongType) {
  return song.artists.length ? song.artists.join(", ") : "Unknown artist";
}

export default function SongSuggestionSlider() {
  const { data: songs } = useContext(SongContext);

  const suggestedSongs = useMemo(() => {
    if (!songs) return songs;
    return shuffle(songs).slice(0, numberOfCards);
  }, [songs]);

  const handleClick = (song: SongType) => {
    navigateToSong(song.key);
  };

  return (
    <>
      {/* <Carousel /> */}
      <Grid container spacing={1.5} alignItems="stretch">
        {suggestedSongs
          ? suggestedSongs.map((song) => (
              <Grid size={{ xs: 12, sm: 6, md: 3 }} key={song.key}>
                <Card
                  elevation={0}
                  sx={{
                    height: 118,
                    borderRadius: 1.5,
                    border: "1px solid rgba(87, 83, 78, 0.14)",
                    bgcolor: "rgba(255, 250, 243, 0.9)",
                    boxShadow: "0 10px 26px rgba(28, 25, 23, 0.06)",
                  }}
                >
                  <CardActionArea
                    onClick={() => handleClick(song)}
                    sx={{
                      "&:focus": {
                        outline: "none",
                      },
                      height: "100%",
                    }}
                  >
                    <CardContent
                      sx={{
                        height: "100%",
                        display: "flex",
                        flexDirection: "column",
                        justifyContent: "center",
                        gap: 0.75,
                        p: 2.25,
                        "&:last-child": { pb: 2.25 },
                      }}
                    >
                      <Box sx={{ minWidth: 0 }}>
                        <Typography
                          variant="h6"
                          sx={{
                            fontWeight: 800,
                            lineHeight: 1.18,
                            fontSize: "1.12rem",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            display: "-webkit-box",
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: "vertical",
                          }}
                        >
                          {song.title}
                        </Typography>
                        <Typography
                          color="text.secondary"
                          sx={{
                            mt: 0.75,
                            fontSize: "0.92rem",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            display: "-webkit-box",
                            WebkitLineClamp: 1,
                            WebkitBoxOrient: "vertical",
                          }}
                        >
                          {getArtists(song)}
                        </Typography>
                      </Box>
                    </CardContent>
                  </CardActionArea>
                </Card>
              </Grid>
            ))
          : [...Array(numberOfCards)].map((_card, index) => (
              <Grid size={{ xs: 12, sm: 6, md: 3 }} key={index}>
                <Skeleton
                  variant="rounded"
                  height={118}
                  sx={{ borderRadius: 1.5 }}
                />
              </Grid>
            ))}
      </Grid>
    </>
  );
}
