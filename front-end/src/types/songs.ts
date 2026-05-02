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
  version: number;
  versions: SongVersionType[];
};

export type SongVersionType = {
  id: number;
  version: number;
  key: string;
  title: string;
  artists: string[];
};

export type AllSongsType = {
  data: SongType[]
}

export type SongURLType = {
  url: string
}
