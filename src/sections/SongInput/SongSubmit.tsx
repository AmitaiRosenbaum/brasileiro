import { Button } from "@mui/material";
import type { SongType } from "../../types/songs";
import type React from "react";

export default function SongSubmit({ song }: { song: SongType | null }) {
  const openSong = (_event: React.MouseEvent) => {
    if (!song) return null;

    window.open(song.path);
  };
  return (
    <Button variant="contained" onClick={(event) => openSong(event)}>
      Find Song
    </Button>
  );
}
