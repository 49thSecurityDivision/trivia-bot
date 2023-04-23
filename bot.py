import discord
import asyncio
import time
import logging

from trivia_prompter import AsyncTriviaStateMachine

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

    def attach_prompter_state_machine(self, machine):
        self._prompter_state_machine = machine

    async def on_ready(self):
        print('on_ready() callback')

        channels = {c.name: c for c in self.get_all_channels()}

        log_channel = channels['bot-logs']

        machine = self._prompter_state_machine
        machine._send_log_func = log_channel.send
        # await machine.log('TriviaBot Connected')

    async def on_message(self, message):
        print('on_message() callback')
        if (message.author == self.user) or (message.is_system()):
            return

        if message.channel.name.lower() != 'bot-logs':
            print("DEBUG: ignore message, confine bot to this channel")
            return

        payload = message.content.strip()
        machine = self._prompter_state_machine

        if payload.startswith('!') and foo.from_admin(message):
            print("Processing command")
            await self.process_command(message)

        elif message.channel == machine.active_channel:
            await machine.process_message(message)

    async def process_command(self, message):
        machine = self._prompter_state_machine

        cmd, *args = message.content.strip().split(' ')
        cmd = cmd.removeprefix('!')

        if cmd == 'stop':
            await machine.stop()

        elif cmd == 'start':
            print("Start")
            await machine.start(message.channel)

        elif cmd == 'state':
            await message.channel.send(f'Bot State is: `{machine.state}`')

        elif cmd in {'invoke', 'dispatch'}:
            # TODO: sanitize/validity checks?
            if args:
                await machine.machine.dispatch(args[0])


if __name__ == '__main__':
    logging.basicConfig(level='INFO')

    with open(".env") as f:
        token = f.read()

    intents = discord.Intents.default()
    intents.typing, intents.presences = False, False
    intents.message_content = True

    bot = TriviaBot(intents=intents)

    machine = AsyncTriviaStateMachine()
    bot.attach_prompter_state_machine(machine)

    bot.run(token)
