
import yaml
import re
import logging

import asyncio
from transitions.extensions.states import add_state_features
from transitions.extensions.asyncio import AsyncTimeout, AsyncMachine

log = logging.getLogger(__name__)


class Prompter:

    def __init__(self):
        self.prompts = []
        self.results = []
        self.current_prompt = None

    def read_question_file(self, filename, question_format='txt'):
        question_parsers = {
            'txt': self._parse_text_questions,
        }

        # TODO: try and get question_format from filename

        parser = question_parsers[question_format]
        with open(filename, 'r') as file:
            questions = parser(file)
            self.prompts += questions
            # TODO: deduplicate while maintaining order?

    def _parse_yaml_questions(self, fp) -> list:
        raise NotImplementedError

    def _parse_text_questions(self, fp) -> list:
        regex = re.compile(
            """(?P<type>question|answer)[:]{0,1} (?P<text>.*\S)""",
            re.IGNORECASE
        )

        data = map(regex.match, fp.readlines())
        data = [match.groupdict() for match in data if match]

        for line in data:
            line['type'] = line['type'].lower()
            assert line['text'].strip()

        questions = data[::2]
        answers = data[1::2]

        for question, answer in zip(questions, answers):
            assert question['type'] == 'question'
            assert answer['type'] == 'answer'
            yield {'question': question['text'], 'answer': answer['text']}


class AsyncHelloWorld:

    def __init__(self):
        self.current_question = None
        self.questions = [f'question_{i}' for i in range(3)]

        self.announce_callback = None

        self._setup_async_machine()

    def _setup_async_machine(self):
        initial_state = 'initial'
        stop_state = 'stopped'

        states = [
            initial_state,
            stop_state,
            'select_question',
            'announce_question',
            'wait_for_answers',
            'checking_answers',

        ]

        machine = AsyncMachine(
            model=self,
            queued=True,
            initial=initial_state,
            states=states,
        )

        machine.add_transition('start', initial_state, 'select_question')
        machine.add_transition('stop', '*', stop_state)

        self.machine = machine

    async def on_enter_select_question(self):
        print("select question")
        if self.questions:
            self.current_question = self.questions.pop(0)
            await self.to_announce_question()
        else:
            await self.stop()

    async def on_enter_announce_question(self):
        msg = f'Question is: {self.current_question}'
        print(msg)

        await self.announce_callback(msg)

        await self.to_wait_for_answers()

    async def on_enter_wait_for_answers(self):
        print("Enter is running")
        await asyncio.sleep(5)

    async def on_enter_checking_answers(self):
        print("checking answers")

    async def __call__(self):
        await self.start()


if __name__ == '__main__':
    logging.basicConfig(level='INFO')
    p = Prompter()
    p.read_question_file('questions.txt')

    thing = AsyncHelloWorld()
    asyncio.run(thing())
