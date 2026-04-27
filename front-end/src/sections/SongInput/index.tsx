import { Stack } from "@mui/material";
import { useState, type SyntheticEvent } from "react";
import type { SongType } from "../../types/songs";
import SongSelector from "./SongSelector";
import SongSubmit from "./SongSubmit";

export default function SongInputComponent() {
  const [song, setSong] = useState<SongType | null>(null);

  return (
    <Stack
      spacing={1.5}
      direction={{ xs: "column", sm: "row" }}
      alignItems="stretch"
    >
      <SongSelector
        song={song}
        onChange={(_event: SyntheticEvent, newSong: SongType | null) =>
          setSong(newSong)
        }
      />
      <SongSubmit song={song} />
    </Stack>
  );
}
