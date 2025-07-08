from pathlib import Path
import csv
import os
import re


SCRIPT_DIR = Path(__file__).parent


def format_files():
    split_dir = SCRIPT_DIR / 'music' / 'split'

    file_names = os.listdir(split_dir)
    all_files = []
    for file_name in file_names:
        words = [word.lower()
                 for word in file_name[:-4].replace('-', ' ').split(' ')]
        all_files.append(words)
    return all_files


def find_closest(name, dir_names):
    scores = []
    for dir_name in dir_names:
        score = len(set(name).intersection(set(dir_name)))
        scores.append(score)
        print(score)
    return scores


def main():
    dir_files = format_files()

    with open(SCRIPT_DIR / 'music' / 'songs.csv', 'r') as file:
        next(file)
        for line in file:
            words = [word.strip().lower()
                     for word in line.split(' ') if word and word != ';']
            scores = find_closest(words, dir_files)
            max_score = max(scores)
            index = scores.index(max_score)
            print('hi')


if __name__ == '__main__':
    main()
