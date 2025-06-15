import type { SongType } from "../../types/songs";
import { axiosFetch } from "../../utils/axios";
import useSWR from "swr";

const endpoints = {
  songUrl: "songs/getSongUrl",
  allSongs: "songs/getAllSongs",
};

export function useSongUrl(songName?: string) {
  const params = { name: songName?.toLowerCase() };
  const { data, ...other } = useSWR(
    songName == null ? null : [endpoints.songUrl, params],
    ([endpoint, params]) => axiosFetch(endpoint, params),
  );

  return { data: data && (data.url as string), ...other };
}

export function useAllSongs() {
  const { data, ...other } = useSWR(endpoints.allSongs, axiosFetch);

  return { data: data && data.data, ...other };
}
