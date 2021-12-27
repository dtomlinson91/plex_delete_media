import csv
import json
import os
import pathlib
import re
from datetime import date
from typing import List

import panaetius
from arrapi import RadarrAPI, NotFound

BASE_URL = "http://10.1.1.50:7878"
API_KEY = os.environ["RADARR_API_KEY"]
HEADER = "plex_delete_media"
DATE_TODAY = date.today().strftime("%Y_%m_%d")


def main() -> None:
    logger = get_logger()
    radarr = RadarrAPI(BASE_URL, API_KEY)

    all_movies = {re.sub("[^A-Za-z0-9 ]+", "", movie.title): movie for movie in radarr.all_movies()}
    movies_to_delete = [movie[0] for movie in get_csv()]

    space_saved: int = 0
    movies_deleted = {"movies_deleted": []}
    movies_not_found = {"movies_not_found": []}

    _deleted_count = 0

    for movie_to_delete in movies_to_delete:
        movie_to_delete = re.sub("[^A-Za-z0-9 ]+", "", movie_to_delete)
        if movie_to_delete in all_movies:
            try:
                all_movies[movie_to_delete].delete(deleteFiles=True)
            except NotFound:
                movies_not_found["movies_not_found"].append({"title": movie_to_delete})
            movie_object = {
                "title": movie_to_delete,
                "year": all_movies[movie_to_delete].year,
                "path": all_movies[movie_to_delete].path,
                "size_on_disk_bytes": all_movies[movie_to_delete].sizeOnDisk,
                "size_on_disk_gb": float(round(all_movies[movie_to_delete].sizeOnDisk / pow(10, 9), 2)),
            }
            _deleted_count += 1
            space_saved += all_movies[movie_to_delete].sizeOnDisk
            movies_deleted["movies_deleted"].append(movie_object)
            logger.info(f"Deleted: {movie_object}")  # noqa
        else:
            movies_not_found["movies_not_found"].append({"title": movie_to_delete})

    _space_saved_gb = int(round(space_saved / pow(10, 9), 0))

    logger.info("Movies deleted: %s", _deleted_count)
    logger.info("Space saved: %sGB", _space_saved_gb)
    logger.info("%s movies could not be found.", len(movies_not_found["movies_not_found"]))

    summary = {
        "_summary": {"movies_deleted": _deleted_count, "space_saved_gb": _space_saved_gb, "date_deleted": DATE_TODAY}
    }
    movies_deleted = {**summary, **movies_deleted}
    save_results(movies_deleted, movies_not_found)


def get_logger() -> None:
    logging_dir = pathlib.Path(__file__).parents[0] / "logs"
    logging_dir.mkdir(parents=True, exist_ok=True)

    config = panaetius.Config("plex_delete_media", skip_header_init=True)
    panaetius.set_config(config, "logging.level", "DEBUG")
    panaetius.set_config(config, "logging.path", logging_dir)

    return panaetius.set_logger(config, panaetius.SimpleLogger(logging_level=config.logging_level))


def save_results(movies_deleted: List, movies_not_found: List) -> None:
    results_dir = pathlib.Path(__file__).parents[0] / "results" / DATE_TODAY
    results_dir.mkdir(parents=True, exist_ok=True)

    movies_deleted_file = (results_dir / "movies_deleted").with_suffix(".json")
    movies_not_found_file = (results_dir / "movies_not_found").with_suffix(".json")

    with movies_deleted_file.open("w") as movies_deleted_file_contents:
        json.dump(movies_deleted, movies_deleted_file_contents, indent=2)

    with movies_not_found_file.open("w") as movies_not_found_file_contents:
        json.dump(movies_not_found, movies_not_found_file_contents, indent=2)


def get_csv() -> List:
    _all_movies = []
    with open(
        pathlib.Path(__file__).parents[0] / "data" / "movies_to_delete.csv", mode="r", encoding="utf-8"
    ) as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            _all_movies.append(row)
    return _all_movies


if __name__ == "__main__":
    main()
