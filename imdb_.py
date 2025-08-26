import re
from imdb import IMDb

ia = IMDb()

IMDB_URL_PATTERN = re.compile(r"(?:https?://)?(?:www\.)?imdb\.com/title/(tt\d+)/?")


async def get_imdb_info(query: str):
    # Case 1: Direct IMDb URL
    match = IMDB_URL_PATTERN.search(query)
    if match:
        movie_id = match.group(1)
        movie = ia.get_movie(movie_id[2:])  # IMDbPY drops the 'tt' prefix
        return movie

    # Case 2: Plaintext search
    search_results = ia.search_movie(query)
    if not search_results:
        return None

    # Use the first result
    movie = ia.get_movie(search_results[0].movieID)
    return movie
