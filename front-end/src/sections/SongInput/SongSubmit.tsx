import { Button } from "@mui/material";
import type React from "react";
import { useSongUrl } from "../../api/hooks/songs";
import type { SongType } from "../../types/songs";

export default function SongSubmit({ song }: { song: SongType | null }) {
  const { data: songUrl, isLoading } = useSongUrl(song);
  const openSong = (_event: React.MouseEvent) => {
    if (!song) return null;
    if (songUrl) {
      window.open(songUrl);
    }
  };
  return (
    <Button
      variant="contained"
      disabled={!song || isLoading}
      onClick={(event) => openSong(event)}
      sx={{
        minHeight: 58,
        px: 4,
        borderRadius: 1.5,
        bgcolor: "#14532d",
        boxShadow: "0 12px 30px rgba(20, 83, 45, 0.22)",
        whiteSpace: "nowrap",
        "&:hover": { bgcolor: "#0f3f23" },
      }}
    >
      Open score
    </Button>
  );
}
