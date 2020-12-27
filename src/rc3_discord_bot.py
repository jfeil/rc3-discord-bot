import configparser
from datetime import datetime, timedelta, timezone
import os
from typing import Any, Dict, List, Optional, Tuple, Union
from discord.embeds import Embed
from discord.enums import ChannelType
from discord.errors import NotFound
from discord.ext import commands, tasks
from discord.message import Message

import pickle

from schedule_planner import SchedulePlanner

class DiscordBot(commands.Bot):
    
    config_path: str
    channels: Dict[int, int]
    messages: Dict[int, Union [Tuple[Message, Message], Tuple[int, int]]]
    events: List[Any]
    token: str
    schedule_planner: SchedulePlanner

    def __init__(self, schedule_planner: SchedulePlanner, config_path:str = "config.json", token: str = ""):
        super().__init__("€")

        self.config_path = config_path

        self.token = token
        self.schedule_planner = schedule_planner
        self.events = []
        self.channels = {}
        self.messages = {}

        if os.path.isfile(config_path):
            with open(config_path, 'rb') as file:
                save_dict = pickle.load(file)
            # self.token = save_dict['token']
            self.channels = save_dict['channels']
            self.messages = save_dict['messages']

        if not self.token:
            return

        self.init_commands()
        self.init_tasks()
        self.run(self.token)

    def init_commands(self):
        self.add_command(self.test)
        self.add_command(self.init_rc3_channel)

    def init_tasks(self):
        self.printer.start()

    def save_config(self):
        save_dict = {
            "token": self.token,
            "channels": self.channels,
            "messages": {guild_id: (self.messages[guild_id][0].id, self.messages[guild_id][1].id) for guild_id in self.messages}
        }

        with open(self.config_path, "wb+") as file:
            pickle.dump(save_dict, file)

    def prepare_message(self) -> Tuple[bool, Optional[Tuple[Tuple[str, Optional[Embed]], Tuple[str, Optional[Embed]]]]]:
        def events_to_embed(events: Dict[str, Any], title: str,  url: str) -> Optional[Embed]:
            if not events:
                return None

            return_embed = Embed(url=url, title=title)
            for event in events:
                description = events[event]["title"]
                starttime = datetime.fromisoformat(events[event]["date"])
                duration = datetime.strptime(events[event]["duration"], "%H:%M")
                duration = timedelta(hours=duration.hour, minutes=duration.minute)
                endtime = starttime + duration
                current_time = datetime.now(tz=timezone(timedelta(seconds=3600)))
                if starttime > current_time:
                    min_text = "in {} min".format(int((starttime - current_time).seconds/60))
                else:
                    min_text = "{} min left".format(int((endtime - current_time).seconds/60))
                date = "{}-{} ({})".format(starttime.strftime("%H:%M"), endtime.strftime("%H:%M"), min_text)
                link = ""
                if 'url' in events[event]:
                    link = events[event]['url']
                return_embed = return_embed.add_field(name=event, value="\n".join([description, date, link]), inline=True)
            return return_embed

        events = self.schedule_planner.current_events()
        if self.events is events:
            return False, None

        current_events = ""
        nextup_events = ""
        current_events_embed = events_to_embed(events[0], "Current events", "https://streaming.media.ccc.de/rc3")
        nextup_events_embed = events_to_embed(events[1], "Upcoming events", "https://rc3.world/rc3/public_fahrplan")

        if not current_events_embed:
            current_events = "There is currently no event ongoing."


        if not nextup_events_embed:
            nextup_events = "There is no event upcoming today."


        return True, ((current_events, current_events_embed), (nextup_events, nextup_events_embed))

    @tasks.loop(minutes=1)
    async def printer(self):
        removed_channels = []

        result, events = self.prepare_message()

        if not result:
            return

        for guild_id in self.messages:
            try:
                guild = self.get_guild(guild_id)
                if not guild:
                    return

                if type(self.messages[guild_id][0]) is Message:
                    current_message = self.messages[guild_id][0]
                    upcoming_message = self.messages[guild_id][1]
                else:
                    channel = guild.get_channel(self.channels[guild_id])

                    current_message = await channel.fetch_message(self.messages[guild_id][0])
                    upcoming_message = await channel.fetch_message(self.messages[guild_id][1])

                    self.messages[guild_id] = (current_message, upcoming_message)

                await self.messages[guild_id][0].edit(content=events[0][0], embed=events[0][1])
                await self.messages[guild_id][1].edit(content=events[1][0], embed=events[1][1])
            except NotFound:
                removed_channels.append(guild_id)

        for item in removed_channels:
            self.channels.pop(item)
            self.messages.pop(item)

    @staticmethod
    @commands.command()
    async def test(ctx, arg): 
        await ctx.send(arg)

    @staticmethod
    @commands.command()
    async def init_rc3_channel(ctx, *args):
        if ctx.channel.type is not ChannelType.text:
            ctx.send("This is just supported within Textchannels! And now go away and leave me alone...")

        if ctx.guild.id in ctx.bot.channels:
            # add check for force -> clear old channel and recreate new channel
            pass

        ctx.bot.channels[ctx.guild.id] = ctx.channel.id
        await ctx.channel.edit(name="rc3-timetable", topic="This updates every x-min to show the current timetable for the rC3 2020" ,reason="rC3 Setup")
        await ctx.channel.purge()
        
        current, upcoming = (await ctx.channel.send(content="Current Placeholder"), await ctx.channel.send(content="Nextup Placeholder"))
        ctx.bot.messages[ctx.guild.id] = current, upcoming

        ctx.bot.save_config()
        ctx.bot.printer.restart()