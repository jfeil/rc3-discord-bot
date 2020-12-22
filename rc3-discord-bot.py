import argparse

json_source = 'https://data.c3voc.de/rC3/everything.schedule.json'

parser = argparse.ArgumentParser('This is a bot for the rC3 program!')
parser.add_argument('-t', '--token', dest='token', required=True, help='This is the *required* discord bot api token!')
parser.add_argument('-u', '--update-rate', dest='rate', required=False, default=3600)


if __name__ == "__main__":
    args = parser.parse_args()
    print(args.token)