import discord
import asyncio
import time
import logging

from operator import itemgetter, attrgetter


class foo:
    @staticmethod
    def from_admin(msg):
        admin_roles = {'Admin'}

        role_names = map(attrgetter('name'), msg.author.roles)
        for role in role_names:
            if role in admin_roles:
                return True
        return False

    @staticmethod
    def is_operator(msg):
        operator_roles = {'Admin', 'Operator', 'Moderator'}

        role_names = map(attrgetter('name'), msg.author.roles)
        for role in role_names:
            if role in operator_roles:
                return True
        return False


class TriviaBot(discord.Client):

    async def on_ready(self):
        print("on_ready called")
        self.active_channel = None

    async def on_message(self, message):
        if message.author == self.user or message.is_system():
            return

        payload = message.content.strip()

        if payload.startswith('!') and foo.from_admin(message):
            await self.process_command(message)
        elif message.channel == self.active_channel:
            await self.process_freeform(message)

    async def process_command(self, message):
        payload = message.content.strip()
        if payload == '!stop':
            self.active_channel = None
            await message.channel.send('Bot is disabled')

        if payload == '!start':
            self.active_channel = message.channel
            await message.channel.send(f'Starting bot in "{message.channel.name}"')

    async def process_freeform(self, message):
        await message.channel.send(f'Your message length was {len(message.content)}')


if __name__ == '__main__':
    logging.basicConfig(level='INFO')

    with open(".env") as f:
        token = f.read()

    intents = discord.Intents.default()
    intents.typing, intents.presences = False, False

    bot = TriviaBot(intents=intents)
    bot.run(token)
