import { Button } from "@mui/material";
import type React from "react";
import { useSongUrl } from "../../api/hooks/songs";
import type { SongType } from "../../types/songs";

export default function SongSubmit({ song }: { song: SongType | null }) {
  const { data: songUrl } = useSongUrl(song);
  const openSong = (_event: React.MouseEvent) => {
    if (!song) return null;
    if (songUrl) {
      window.open(songUrl);
    }
    console.log(songUrl);
  };
  return (
    <Button variant="contained" onClick={(event) => openSong(event)}>
      Find Song
    </Button>
  );
}
