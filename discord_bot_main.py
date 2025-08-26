import os
from dotenv import load_dotenv

import discord
from discord import app_commands

from movie_data import setup, add_movie, add_rating, get_movie_info, get_movies  # grab database methods
from imdb_ import get_imdb_info  # grab imdb methods

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


class RatingButton(discord.ui.Button):
    def __init__(self, rating: int, guild_id: int, movie_id: int):
        # Label is stars instead of number
        stars = "" + ("⭐" * (rating // 2))
        if rating % 2 != 0:
            stars += "[⭐/2]"
        print("")
        super().__init__(label=stars, style=discord.ButtonStyle.primary, row=(rating - 1) // 5)
        self.rating = rating
        self.guild_id = guild_id
        self.movie_id = movie_id

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        await add_rating(self.guild_id, self.movie_id, self.rating, user_id)
        await interaction.response.send_message(
            f"You rated this movie {self.rating}⭐",
            ephemeral=True
        )


class RatingView(discord.ui.View):
    def __init__(self, guild_id: int, movie_id: int):
        super().__init__(timeout=None)
        for i in range(1, 11):  # 1⭐ through 10⭐
            self.add_item(RatingButton(i, guild_id, movie_id))


@client.event
async def on_ready():
    try:
        await tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ Synced commands to guild {GUILD_ID}")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")
    try:
        await setup()  # This creates the table on startup!
    except Exception as e:
        print(f"❌ DB config error: {e}")
    print(f"✅ Logged in as {client.user}")


@tree.command(name="start_movie", description="Start watching a movie", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(name="The name or IMDb link of the movie")
async def movie_start(interaction: discord.Interaction, name: str):
    await interaction.response.defer()
    movie = await get_imdb_info(name)

    if not movie:
        await interaction.followup.send("Sorry, I couldn't find a matching movie.")
        return

    title = movie.get('title', 'Unknown Title')
    year = movie.get('year', 'Unknown Year')
    imdb_link = f"https://www.imdb.com/title/tt{movie.movieID}/"

    # Send the movie message with rating buttons
    view = RatingView(interaction.guild_id, int(movie.movieID))
    await interaction.followup.send(f"**{title} ({year})**\n{imdb_link}", view=view)

    # Save to DB
    await add_movie(interaction.guild_id, movie, title)
    print(f"{movie} added to db")


@tree.command(name="rank_movie", description="View movie info and ratings", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(name="The name or IMDb link of the movie to look up")
async def movie_view(interaction: discord.Interaction, name: str):
    """Fetch info about a stored movie by searching IMDb first and matching ID."""
    await interaction.response.defer()

    # Search IMDb first
    movie = await get_imdb_info(name)
    if not movie:
        await interaction.followup.send("Couldn't find a matching movie on IMDb.")
        return

    imdb_id = int(movie.movieID)
    # Query DB for that movie_id
    movie_info = await get_movie_info(interaction.guild_id, imdb_id=imdb_id)  # we'll adapt get_movie_info

    if not movie_info:
        await interaction.followup.send("Movie not found in the database for this guild.")
        return

    msg = f"**{movie_info['title']} ({movie_info['year']})**\n"
    msg += f"Average Rating: {movie_info['avg_rating']}/10 from {movie_info['total_ratings']} ratings."
    await interaction.followup.send(msg)


@tree.command(name="movie_leaderboard", description="Show the top rated movies for this server",
              guild=discord.Object(id=GUILD_ID))
async def movie_leaderboard(interaction: discord.Interaction):
    """Pulls all movies from DB for this guild and shows a leaderboard."""
    await interaction.response.defer()

    # get_movies should return a list of dicts or tuples: (title, avg_rating, total_ratings)
    movies = await get_movies(interaction.guild_id)

    if not movies:
        await interaction.followup.send("No movies or ratings found yet for this server.")
        return

    # Build a leaderboard text, e.g., top 10
    leaderboard_lines = []
    for idx, movie in enumerate(movies[:10], start=1):
        # Adapt based on how get_movies returns data
        # If it's dict: movie['title'], movie['avg_rating'], movie['total_ratings']
        # If it's tuple: (title, avg_rating, total_ratings)
        title = movie['title'] if isinstance(movie, dict) else movie[0]
        avg_rating = movie['avg_rating'] if isinstance(movie, dict) else movie[1]
        total_ratings = movie['total_ratings'] if isinstance(movie, dict) else movie[2]

        leaderboard_lines.append(
            f"{idx}. **{title}** — {avg_rating:.1f}/10 ({total_ratings} ratings)"
        )

    msg = "**Movie Leaderboard:**\n" + "\n".join(leaderboard_lines)
    await interaction.followup.send(msg)


client.run(TOKEN)
