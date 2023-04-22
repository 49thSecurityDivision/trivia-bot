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

    def attach_prompter(self, prompter):
        self.prompter = prompter

    async def on_ready(self):
        print("on_ready called")

        channels = {chan.name: chan for chan in self.get_all_channels()}

        logging_channel = channels['admin']

        self.prompter.announce_callback = logging_channel.send

    async def on_message(self, message):
        if message.author == self.user:
            return

        # Verify this does what I think it does
        if message.is_system():
            return

        if message.channel.name != 'admin':
            return

        if not foo.from_admin(message):
            return

        print(message)
        self._test_message = message

        if message.content.strip().lower() == "this is a test of the bot being able to send messages":
            await message.channel.send(f'Test Response')

        payload = message.content.strip().lower()

        if payload == '!start':
            await self.prompter()


if __name__ == '__main__':
    logging.basicConfig(level='INFO')

    with open(".env") as f:
        token = f.read()

    prompter = Prompter()
    prompter.read_question_file('questions.txt')

    from trivia_prompter import AsyncHelloWorld
    prompter = AsyncHelloWorld()

    intents = discord.Intents.default()
    intents.typing, intents.presences = False, False

    bot = TestBot(intents=intents)
    bot.attach_prompter(prompter)
    bot.run(token)
