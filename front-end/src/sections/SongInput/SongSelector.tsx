import { Autocomplete, CircularProgress, TextField } from "@mui/material";
import { useState, type SyntheticEvent } from "react";
import type { SongType } from "../../types/songs";
import { useAllSongs } from "../../api/hooks/songs";

export default function SongSelector({
  song,
  onChange,
}: {
  song: SongType | null;
  onChange: (_event: SyntheticEvent, newSong: SongType | null) => void;
}) {
  const { data, isLoading } = useAllSongs();
  const [open, setOpen] = useState(false)

  const getOptionLabel = (song: SongType): string => {
    if (!song.artists || !song.artists.length) {
      return song.title;
    } else {
      return `${song.title} - ${song.artists.join(", ")}`;
    }
  };

  return (
    <Autocomplete
      disablePortal
      options={data ?? []}
      value={song}
      onChange={onChange}
      onOpen={() => setOpen(true)}
      onClose={() => setOpen(false)}
      getOptionLabel={getOptionLabel}
      fullWidth
      loading={isLoading}
      renderInput={(params) => (
        <TextField {...params} label="I want to play..." slotProps={{input: {
          ...params.InputProps,
          endAdornment: (
            <>{(isLoading && open) ? <CircularProgress color="inherit" size={20} /> : null}
            {params.InputProps.endAdornment}</>
          )
        }}}/>
      )}
    />
  );
}
