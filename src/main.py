import argparse
import datetime

from schedule_planner import SchedulePlanner 
from rc3_discord_bot import DiscordBot

json_source = 'https://data.c3voc.de/rC3/everything.schedule.json'

parser = argparse.ArgumentParser('This is a bot for the rC3 program!')
parser.add_argument('-t', '--token', dest='token', required=False, help='This is the *required* discord bot api token!', default=None)
parser.add_argument('-u', '--update-rate', dest='rate', required=False, default=3600)


if __name__ == "__main__":
    args = parser.parse_args()

    schedule_planner = SchedulePlanner(json_source)
    schedule_planner.current_events(datetime.datetime.fromtimestamp(1609104000, tz=datetime.timezone(datetime.timedelta(seconds=3600))))

    bot = DiscordBot(schedule_planner, token=args.token)
