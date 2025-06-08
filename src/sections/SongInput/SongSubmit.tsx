import { Button } from "@mui/material";
import type { SongType } from "../../types/songs";

export default function SongSubmit({ song }: { song: SongType | null }) {
  return <Button variant="contained">Find Song</Button>;
}
