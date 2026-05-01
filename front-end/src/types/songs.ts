export type SongTypeOLD = {
  name: string;
  path: string;
  artist?: string;
  year?: number;
  songLink?: string;
};

export type SongType = {
  id: number;
  title: string;
  artists: string[];
  key: string;
};
export type AllSongsType = {
  data: SongType[]
}

export type SongURLType = {
  url: string
}
