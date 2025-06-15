from pathlib import Path
import csv
import os
import shutil


SCRIPT_DIR = Path(__file__).parent


def write_files():
    split_dir = SCRIPT_DIR / 'music' / 'split'

    file_names = os.listdir(split_dir)
    file_names.sort(key=lambda x: int(x.split('-')[0]))

    for file_name in file_names:
        with open(SCRIPT_DIR / 'music' / 'renaming_files.csv', 'a') as file:
            title, artist = file_name[:-4].split('-')[1:3]
            file.write(f'{title}; {artist}; {file_name}\n')


def main():
    split_dir = SCRIPT_DIR / 'music' / 'split'
    dest_path = SCRIPT_DIR / 'music' / 'final'
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    file_names = os.listdir(split_dir)
    file_names.sort(key=lambda x: int(x.split('-')[0]))

    with open(SCRIPT_DIR / 'music' / 'corrected_songs.csv', 'r') as file:
        next(file)
        for i, line in enumerate(file):
            artist, title = line.split(';')
            updated_name = f'{title.strip()}_{artist.strip()}.pdf'
            old_name = file_names[i]
            shutil.copy2(
                split_dir / old_name, dest_path / updated_name)


if __name__ == '__main__':
    main()
