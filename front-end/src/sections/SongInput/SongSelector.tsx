import { Autocomplete, TextField } from "@mui/material";
import songs from "../../api/static-api-data";
import type { SyntheticEvent } from "react";
import type { SongType, SongTypeOLD } from "../../types/songs";
import { useAllSongs } from "../../api/hooks/songs";

export default function SongSelector({
  song,
  onChange,
}: {
  song: SongType | null;
  onChange: (_event: SyntheticEvent, newSong: SongType | null) => void;
}) {
  const { data } = useAllSongs();
  // console.log("🚀 ~ data:", data);

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
      options={data}
      value={song}
      onChange={onChange}
      getOptionLabel={getOptionLabel}
      fullWidth
      renderInput={(params) => (
        <TextField {...params} label="Search for a song" />
      )}
    />
  );
}
