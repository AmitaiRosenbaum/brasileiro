import { Autocomplete, TextField } from "@mui/material";
import songs from "../../api/static-api-data";
import type { SyntheticEvent } from "react";
import type { SongType } from "../../types/songs";

export default function SongSelector({
  song,
  onChange,
}: {
  song: SongType | null;
  onChange: (_event: SyntheticEvent, newSong: SongType | null) => void;
}) {
  return (
    <Autocomplete
      disablePortal
      options={songs}
      value={song}
      onChange={onChange}
      getOptionLabel={(song) => song.name}
      fullWidth
      renderInput={(params) => (
        <TextField {...params} label="Search for a song" />
      )}
    />
  );
}
