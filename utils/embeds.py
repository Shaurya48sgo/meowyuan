import discord

COLOR_INFO = 0x2B2D31
COLOR_SUCCESS = 0x43B581
COLOR_ERROR = 0xF04747
COLOR_WARNING = 0xFAA61A


def info_embed(title: str, description: str = None, private: bool = False) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=COLOR_INFO)
    embed.set_footer(text="Private" if private else None)
    return embed


def success_embed(title: str, description: str = None) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=COLOR_SUCCESS)


def error_embed(title: str, description: str = None) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=COLOR_ERROR)


def warning_embed(title: str, description: str = None) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=COLOR_WARNING)
