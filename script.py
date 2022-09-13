from discord.ext import commands
from dotenv import load_dotenv
from pymongo import MongoClient
import discord, os

load_dotenv()
bot = commands.Bot(command_prefix='!', intents=discord.Intents().all())
client = MongoClient(os.getenv('MONGODB_URL'))

@bot.command()
async def create(ctx, channel_name):
    if already_added_document('{}#{}'.format(ctx.message.author.name, ctx.message.author.discriminator)):
        await already_created_category_and_channel(ctx)
    else:
        if ctx.message.author.activities == None:
            await no_activities_accessible(ctx)
        else:
            if await is_game_or_playing(ctx, False):
                for activity in ctx.message.author.activities:
                    if await is_game_or_playing(ctx, True, activity):
                        if not exists(activity.name, channel_name):
                            if any(category.name == activity.name for category in ctx.message.guild.categories):
                                if any(channel.name == channel_name for channel in find(ctx.message.guild.categories, activity.name).channels):
                                    await channel_already_exists_in_category(ctx. activity, channel_name)
                                else:
                                    category = find(ctx.message.guild.categories, activity.name)
                                    channel = await category.create_voice_channel(name=channel_name)
                                    
                                    await channel_created_successfully(ctx, channel_name)
                                    add_to_db(category.id, activity.name, channel.id, channel_name, '{}#{}'.format(ctx.message.author.name, ctx.message.author.discriminator))
                            else:
                                category = await ctx.message.guild.create_category(name=activity.name)
                                channel = await category.create_voice_channel(name=channel_name)
                                
                                await channel_created_successfully(ctx, channel_name)
                                add_to_db(category.id, activity.name, channel.id, channel_name, '{}#{}'.format(ctx.message.author.name, ctx.message.author.discriminator))
                        else:
                            await channel_already_exists_in_category(ctx, channel_name)
                    else:
                        await not_playing_any_games(ctx)
            else:
                await not_playing_any_games(ctx)

@bot.command()
async def delete(ctx, channel_name):
    channel_id = get_channel_id_by_name(lower_string(channel_name))['channel_id']
    voice_channel = ctx.message.guild.get_channel(channel_id)
    
    if len(voice_channel.members) == 0:
        await delete_channel_and_category(ctx, channel_id)
        remove_from_db(channel_id, '{}#{}'.format(ctx.message.author.name, ctx.message.author.discriminator))
        await channel_deleted_successfully(ctx, channel_name)
    else:
        await channel_is_in_use(ctx, voice_channel.name, voice_channel.category.name)

@bot.command()
async def lock(ctx):
    channel = ctx.message.author.voice.channel
    category = channel.category
    
    user_name = '{}#{}'.format(ctx.message.author.name, ctx.message.author.discriminator)
    if is_owner_of_channel(category.name, channel.name, user_name):
        voice_channel = ctx.message.guild.get_channel(channel.id)
        count = len(voice_channel.members)
        await voice_channel.edit(user_limit=count) if not voice_channel.user_limit == count else await voice_channel.edit(user_limit=0)
        await delete_user_message(ctx)


async def is_game_or_playing(ctx, for_activity, activity=None):
    if for_activity:
        return type(activity) is discord.Game or activity.type == discord.ActivityType.playing
    else:
        return any(isinstance(item, discord.Game) for item in ctx.message.author.activities) or any(item.type == discord.ActivityType.playing for item in ctx.message.author.activities)

async def delete_channel_and_category(ctx, channel_id):
    channel = ctx.message.guild.get_channel(channel_id)
    category = channel.category
    await channel.delete()
    
    if len(category.channels) == 0:
        await category.delete()

async def delete_user_message(ctx):
    await ctx.message.delete()

async def no_activities_accessible(ctx):
    response = await ctx.send('[!]: You do not currently have any activities accessible | {}'.format(ctx.message.author.mention))
    await delete_user_message(ctx)
    await response.delete(delay=5.0)

async def not_playing_any_games(ctx):
    response = await ctx.send('[!]: You are not currently playing any games. Voico requires an active game for accurate category naming | {}'.format(ctx.message.author.mention))
    await delete_user_message(ctx)
    await response.delete(delay=5.0)


async def already_created_category_and_channel(ctx):
    response = await ctx.send('[!]: You have already created a category and channel. Please delete the existing one before creating a new one | {}\n``` !delete name_of_channel ```'.format(ctx.message.author.mention))
    await delete_user_message(ctx)
    await response.delete(delay=5.0)

async def channel_already_exists_in_category(ctx, activity, channel_name):
    response = await ctx.send('[!]: A channel already exists with the name **{}** in the category **{}** | {}'.format(channel_name, activity.name, ctx.message.author.mention))
    await delete_user_message(ctx)
    await response.delete(delay=5.0)

async def channel_created_successfully(ctx, channel_name):
    response = await ctx.send('**{}** has been created successfully | {}'.format(channel_name, ctx.message.author.mention))
    await delete_user_message(ctx)
    await response.delete(delay=5.0)

async def channel_deleted_successfully(ctx, channel_name):
    response = await ctx.send('**{}** has been deleted successfully | {}'.format(channel_name, ctx.message.author.mention))
    await delete_user_message(ctx)
    await response.delete(delay=5.0)

async def channel_is_in_use(ctx, channel_name, category_name):
    response = await ctx.send('[!]: Unable to delete **{}** in **{}** as it\'s still in use | {}'.format(channel_name, category_name, ctx.message.author.mention))
    await delete_user_message(ctx)
    await response.delete(delay=5.0)


def lower_string(str):
    print(str.lower())
    return str.lower()


def find(categories, name):
    for category in categories:
        if category.name == name:
            return category


def add_to_db(category_id, category_name, channel_id, channel_name, user_name):
    client.database.voice_clients.insert_one({
        'category_id' : category_id,
        'category_name' : lower_string(category_name),
        'channel_id' : channel_id,
        'channel_name' : lower_string(channel_name),
        'user_name' : lower_string(user_name)
    })

def already_added_document(user_name):
    return bool(client.database.voice_clients.find_one({
        'user_name' : lower_string(user_name)
    }))

def exists(category_name, channel_name):
    return bool(client.database.voice_clients.find_one({
        'category_name' : lower_string(category_name),
        'channel_name' : lower_string(channel_name)
    }))

def get_channel_id_by_name(channel_name):
    return client.database.voice_clients.find_one({
        'channel_name' : lower_string(channel_name)
    })

def is_owner_of_channel(category_name, channel_name, user_name):
    return bool(client.database.voice_clients.find_one({
        'category_name' : lower_string(category_name),
        'channel_name' : lower_string(channel_name),
        'user_name' : lower_string(user_name)
    }))

def remove_from_db(channel_id, user_name):
    client.database.voice_clients.delete_one({
        'channel_id' : channel_id,
        'user_name' : lower_string(user_name)
    })

bot.run(os.getenv('DISCORD_TOKEN'))