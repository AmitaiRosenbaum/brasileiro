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
  book: BookType | null;
  book_title: string;
  book_song_index: number | null;
};

export type AllSongsType = {
  data: SongType[];
  pagination?: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
    has_next: boolean;
    has_previous: boolean;
    sections?: string[];
  };
};

export type SongURLType = {
  url: string
}

export type ArtistType = {
  id: number;
  name: string;
  birth?: string | null;
  death?: string | null;
};

export type BookType = {
  id: number;
  title: string;
  cover_image?: string;
};
