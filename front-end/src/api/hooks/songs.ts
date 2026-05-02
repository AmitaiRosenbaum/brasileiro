import type { SongType, SongVersionType } from "../../types/songs";
import { axiosFetch } from "../../utils/axios";
import useSWR from "swr";
import type { AllSongsType, SongURLType } from "../../types/songs";

const endpoints = {
  songUrl: "songs/getSongUrl",
  allSongs: "songs/getAllSongs",
};

export function useSongUrl(song: SongType | SongVersionType | null) {
  const params = { id: song?.id };
  const { data, ...other } = useSWR(
    song == null ? null : [endpoints.songUrl, params],
    ([endpoint, params]) => axiosFetch<SongURLType>(endpoint, params),
    {
      revalidateOnFocus: false,
      revalidateIfStale: false,
      revalidateOnReconnect: false,
    },
  );

  return { data: data && (data.url as string), ...other };
}

export function useAllSongs() {
  const { data, ...other } = useSWR(
    endpoints.allSongs,
    axiosFetch<AllSongsType>,
  );

  return { data: data && data.data, ...other };
}
