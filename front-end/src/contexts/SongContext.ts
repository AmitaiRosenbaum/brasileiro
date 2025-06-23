import { createContext } from "react";
import type { SongType } from "../types/songs";

const SongContext = createContext<{
  data: SongType[] | undefined;
  isLoading: boolean;
}>({ data: [], isLoading: false });

export default SongContext;
