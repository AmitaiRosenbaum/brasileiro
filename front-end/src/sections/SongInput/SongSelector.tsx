import { Autocomplete, CircularProgress, TextField } from "@mui/material";
import { useState, type SyntheticEvent } from "react";
import type { SongType } from "../../types/songs";
import { useSongSearch } from "../../api/hooks/songs";

export default function SongSelector({
  song,
  onChange,
}: {
  song: SongType | null;
  onChange: (_event: SyntheticEvent, newSong: SongType | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const { data, isLoading } = useSongSearch(inputValue);

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
      open={open && inputValue.trim().length > 0}
      options={data ?? []}
      value={song}
      inputValue={inputValue}
      onChange={onChange}
      onInputChange={(_event, value) => setInputValue(value)}
      onOpen={() => setOpen(true)}
      onClose={() => setOpen(false)}
      getOptionLabel={getOptionLabel}
      isOptionEqualToValue={(option, value) => option.id === value.id}
      fullWidth
      loading={isLoading}
      noOptionsText={inputValue.trim() ? "No songs found" : ""}
      renderInput={(params) => (
        <TextField
          {...params}
          placeholder="Search by song or artist"
          slotProps={{
            input: {
              ...params.InputProps,
              sx: {
                bgcolor: "#fffaf3",
                borderRadius: 1.5,
                minHeight: 58,
                fontSize: 17,
              },
              endAdornment: (
                <>
                  {isLoading && open ? (
                    <CircularProgress color="inherit" size={20} />
                  ) : null}
                  {params.InputProps.endAdornment}
                </>
              ),
            },
          }}
        />
      )}
    />
  );
}
