import sqlite3
import imdb.Movie

DB_FILE = "bot_data.db"


async def setup():
    with sqlite3.connect(DB_FILE) as db:
        # Table for movies: now includes plaintext title and year
        db.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            guild_id INTEGER,
            movie_id INTEGER,
            title TEXT,
            year INTEGER,
            PRIMARY KEY (guild_id, movie_id)
        )
        """)
        # Table for ratings
        db.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            guild_id INTEGER,
            movie_id INTEGER,
            user_id INTEGER,
            rating INTEGER,
            PRIMARY KEY (guild_id, movie_id, user_id)
        )
        """)
        db.commit()


async def add_movie(guild_id: int, movie: imdb.Movie.Movie, plaintext_title: str = None):
    """
    Adds a movie to the database with plaintext title and year.
    If title not provided, fallback to movie['title'].
    """
    title = plaintext_title or movie.get('title', 'Unknown Title')
    year = movie.get('year', None)
    with sqlite3.connect(DB_FILE) as db:
        db.execute("""
            INSERT OR IGNORE INTO movies (guild_id, movie_id, title, year)
            VALUES (?, ?, ?, ?)
        """, (guild_id, int(movie.movieID), title, year))
        db.commit()


async def add_rating(guild_id: int, movie_id: int, rating: int, user_id: int):
    with sqlite3.connect(DB_FILE) as db:
        db.execute("""
            INSERT INTO ratings (guild_id, movie_id, user_id, rating)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, movie_id, user_id)
            DO UPDATE SET rating=excluded.rating
        """, (guild_id, movie_id, user_id, rating))
        db.commit()


async def get_movies(guild_id: int, limit: int = 25):
    """
    Returns list of top movies for a guild with avg ratings and total ratings.
    Results are sorted by avg_rating DESC and capped at `limit`.
    """
    with sqlite3.connect(DB_FILE) as db:
        cur = db.execute(f"""
            SELECT m.movie_id, m.title, m.year,
                   IFNULL(AVG(r.rating), 0) AS avg_rating,
                   COUNT(r.user_id) AS total_ratings
            FROM movies m
            LEFT JOIN ratings r
              ON m.guild_id = r.guild_id AND m.movie_id = r.movie_id
            WHERE m.guild_id = ?
            GROUP BY m.movie_id
            ORDER BY avg_rating DESC
            LIMIT ?
        """, (guild_id, limit))
        rows = cur.fetchall()
        return [
            {
                "movie_id": r[0],
                "title": r[1],
                "year": r[2],
                "avg_rating": round(r[3], 2) if r[3] is not None else 0,
                "total_ratings": r[4]
            }
            for r in rows
        ]




async def get_movie_info(guild_id: int, title: str = None, imdb_id: int = None):
    """
    Returns movie info by plaintext title or by IMDb movie_id.
    """
    with sqlite3.connect(DB_FILE) as db:
        if imdb_id is not None:
            cur = db.execute("""
                SELECT movie_id, title, year FROM movies
                WHERE guild_id = ? AND movie_id = ?
            """, (guild_id, imdb_id))
        else:
            cur = db.execute("""
                SELECT movie_id, title, year FROM movies
                WHERE guild_id = ? AND LOWER(title) = LOWER(?)
            """, (guild_id, title))

        movie_row = cur.fetchone()
        if not movie_row:
            return None

        movie_id, title, year = movie_row
        cur = db.execute("""
            SELECT AVG(rating), COUNT(*)
            FROM ratings
            WHERE guild_id = ? AND movie_id = ?
        """, (guild_id, movie_id))
        avg, count = cur.fetchone()
        avg_rating = round(avg, 2) if avg is not None else "N/A"

        return {
            "movie_id": movie_id,
            "title": title,
            "year": year,
            "avg_rating": avg_rating,
            "total_ratings": count
        }

