import { axiosFetch } from "../../utils/axios";
import useSWR from "swr";

const endpoints = {
  songUrl: "songs/getSongUrl",
};

export function useSongUrl(songName?: string) {
  const params = { name: songName?.toLowerCase() };
  const { data, ...other } = useSWR(
    songName == null ? null : [endpoints.songUrl, params],
    ([endpoint, params]) => axiosFetch(endpoint, params),
  );

  return { data: data.url as string, ...other };
}
