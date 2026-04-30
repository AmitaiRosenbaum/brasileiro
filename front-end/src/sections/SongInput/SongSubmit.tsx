import { Button } from "@mui/material";
import type { SongType } from "../../types/songs";
import { navigateToSong } from "../../utils/navigation";

export default function SongSubmit({ song }: { song: SongType | null }) {
  const openSong = () => {
    if (!song) {
      return;
    }

    navigateToSong(song.key);
  };

  return (
    <Button
      variant="contained"
      disabled={!song}
      onClick={openSong}
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
