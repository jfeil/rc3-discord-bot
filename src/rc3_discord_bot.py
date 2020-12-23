import configparser
from datetime import datetime, timedelta
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
    messages: Dict[int, Tuple[int, int]]
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
            self.token = save_dict['token']
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
            "messages": self.messages
        }

        with open(self.config_path, "wb+") as file:
            pickle.dump(save_dict, file)


    async def is_ready(self) -> bool:
        print("help")
        return super().is_ready()

    def prepare_message(self) -> Tuple[bool, Optional[Tuple[Tuple[str, Optional[Embed]], Tuple[str, Optional[Embed]]]]]:
        def events_to_embed(events: Dict[str, Any]) -> Optional[Embed]:
            if not events:
                return None

            return_embed = Embed()
            for event in events:
                description = events[event]["title"]
                starttime = datetime.fromisoformat(events[event]["date"])
                duration = datetime.strptime(events[event]["duration"], "%H:%M")
                duration = timedelta(hours=duration.hour, minutes=duration.minute)
                endtime = starttime + duration
                date = "{}-{} ({} min)".format(starttime.strftime("%H:%M"), endtime.strftime("%H:%M"), int(duration.total_seconds()/60))
                return_embed = return_embed.add_field(name=event, value="\n".join([description, date]), inline=True)
            return return_embed

        events = self.schedule_planner.current_events()
        if self.events is events:
            return False, None

        current_events = "Current events"
        nextup_events = "Upcoming events"
        current_events_embed = events_to_embed(events[0])
        nextup_events_embed = events_to_embed(events[1])

        if not current_events_embed:
            current_events = "There is currently no event ongoing."


        if not nextup_events_embed:
            nextup_events = "There is no event upcoming today."


        return True, ((current_events, current_events_embed), (nextup_events, nextup_events_embed))

    @tasks.loop(seconds=1)
    async def printer(self):
        removed_channels = []

        result, events = self.prepare_message()


        if not result:
            return

        for element in self.messages:
            try:
                guild = self.get_guild(element)
                if not guild:
                    return
                channel = guild.get_channel(self.channels[element])

                current_message = await channel.fetch_message(self.messages[element][0])
                upcoming_message = await channel.fetch_message(self.messages[element][1])
                await current_message.edit(content=events[0][0], embed=events[0][1])
                await upcoming_message.edit(content=events[1][0], embed=events[1][1])
            except NotFound:
                removed_channels.append(element)

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
        ctx.bot.messages[ctx.guild.id] = current.id, upcoming.id

        test = ctx.bot.get_guild(ctx.guild.id)

        ctx.bot.save_config()