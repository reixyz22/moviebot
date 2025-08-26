import sqlite3
import imdb.Movie

DB_FILE = "bot_data.db"


async def setup():
    with sqlite3.connect(DB_FILE) as db:
        # Table for movies
        db.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            guild_id INTEGER,
            movie_id INTEGER,
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


async def add_movie(guild_id: int, movie: imdb.Movie.Movie):
    with sqlite3.connect(DB_FILE) as db:
        db.execute(
            "INSERT OR IGNORE INTO movies (guild_id, movie_id) VALUES (?, ?)",
            (guild_id, int(movie.movieID))
        )
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
