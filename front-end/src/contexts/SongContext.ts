import { createContext, useContext } from "react";
import type { SongType } from "../types/songs";

const SongContext = createContext<{
  data: SongType[] | undefined;
  isLoading: boolean;
}>({ data: [], isLoading: false });

export default SongContext;

// function useSongContext() {
//   const songs = useAllSongs()
//   const context = useContext(SongContext);

//   if (context.length === 0) {

//     return null
//   } else {
//     return context
//   }
// }
