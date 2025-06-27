import {
  Card,
  CardActionArea,
  CardContent,
  Grid,
  Skeleton,
  Typography,
} from "@mui/material";
import React, { useContext, useEffect, useMemo, useRef, useState } from "react";
import SongContext from "../../contexts/SongContext";
import { shuffle } from "../../utils/shuffle";
import { useSongUrl } from "../../api/hooks/songs";
import type { SongType } from "../../types/songs";

const numberOfCards = 8;

export default function SongSuggestionSlider() {
  const [selectedSong, setSelectedSong] = useState<SongType | null>(null);
  const { data: songs } = useContext(SongContext);
  const { data: songUrl } = useSongUrl(selectedSong);
  const opened = useRef(false);

  const suggestedSongs = useMemo(() => {
    if (!songs) return songs;
    return shuffle(songs).slice(0, numberOfCards);
  }, [songs]);

  const handleClick = (
    _event: React.MouseEvent<HTMLButtonElement>,
    song: SongType,
  ) => {
    opened.current = false;
    setSelectedSong(song);
  };

  useEffect(() => {
    if (songUrl != null && !opened.current) {
      window.open(songUrl);
      opened.current = true;
    }
  }, [songUrl]);

  return (
    <>
      {/* <Carousel /> */}
      <Grid container spacing={2} alignItems="stretch">
        {suggestedSongs
          ? suggestedSongs.map((song, index) => (
              <Grid size={3} key={index}>
                <Card sx={{ height: 150 }}>
                  <CardActionArea
                    onClick={(_event) => handleClick(_event, song)}
                    sx={{
                      "&:focus": {
                        outline: "none",
                      },
                      height: "100%",
                    }}
                  >
                    <CardContent>
                      <Typography gutterBottom color="text.secondary">
                        {song.artists.length
                          ? song.artists.reduce(
                              (all, artist) => all + " & " + artist,
                            )
                          : ""}
                      </Typography>
                      <Typography variant="h6">{song.title}</Typography>
                    </CardContent>
                  </CardActionArea>
                </Card>
              </Grid>
            ))
          : [...Array(numberOfCards)].map((_card, index) => (
              <Grid size={3} key={index}>
                <Skeleton height={150}></Skeleton>
              </Grid>
            ))}
      </Grid>
    </>
  );
}
