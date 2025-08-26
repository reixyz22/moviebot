import os
from dotenv import load_dotenv

import discord
from discord import app_commands

from movie_data import setup, add_movie, add_rating  # grab database methods
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
            stars += ".5"
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

    if GUILD_ID == 184563986342215680:
        print(" ✅ Fevicord")
    else:
        print("Dev")


@tree.command(name="start", description="Start watching a movie", guild=discord.Object(id=GUILD_ID))
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
    await add_movie(interaction.guild_id, movie)
    print(f"{movie} added to db")


client.run(TOKEN)
