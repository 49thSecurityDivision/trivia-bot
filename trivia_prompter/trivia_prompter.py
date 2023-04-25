
import yaml
import re
import logging

import asyncio
from transitions.extensions.states import add_state_features
from transitions.extensions.asyncio import AsyncTimeout, AsyncMachine


from fastDamerauLevenshtein import damerauLevenshtein


log = logging.getLogger(__name__)


class Prompter:

    def __init__(self):

        self.current_prompt = None
        self.prompts = []
        self.results = []

        self.attempt_buffer = []

    @staticmethod
    def string_distance(correct, attempt):
        correct = correct.strip().lower()
        attempt = attempt.strip().lower()

        # Perform additional normalization against the attempt
        # We are assuming the questions are more standardized
        attempt = attempt.replace('\t', ' ')

        # Do we actually want to do this everytime? Or just strip *all* whitespace?
        attempt = (word for word in attempt.split(' ') if word.strip())
        attempt = ' '.join(attempt)

        return damerauLevenshtein(correct, attempt)

    def score(self, attempt):
        correct = self.current_prompt['answer']
        return self.string_distance(correct, attempt)

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

    def has_prompts(self):
        return bool(self.prompts)

    def next_prompt(self):
        self.attempt_buffer.clear()
        self.current_prompt = self.prompts.pop(0)

        return self.current_prompt

    def add_attempt(self, text):
        pass


class AsyncTriviaStateMachine:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: accept an initilized prompter somehow
        self._prompter = Prompter()
        self._prompter.prompts.append({
            'question': 'hello world',
            'answer': 'hello world',
        })

        self.active_channel = None
        self._send_log_func = None
        self._send_msg_func = None

        self._setup_async_machine()

    def _setup_async_machine(self):
        initial_state = 'initial'
        stop_state = 'stopped'
        states = [
            initial_state,
            stop_state,
            'error',

            'set_channel',
            'select_question',
            'announce_question',
            'wait_for_answers',
            'checking_answers',
            'decide_winner',
            'vote_for_winner',
            'announce_result',
        ]

        machine = AsyncMachine(
            model=self,
            initial=initial_state,
            states=states,
        )

        machine.add_transition(
            'start', [initial_state, stop_state], 'set_channel')
        machine.add_transition('stop', '*', stop_state)

        self.machine = machine

    async def log(self, msg):
        # log.debug(msg) # TODO
        print(msg)

        if not self._send_log_func:
            log.warning('no log func set')
            return

        await self._send_log_func(f'[log]: {msg}')

    async def send_msg(self, msg):
        # log.info(msg) # TODO
        print(msg)

        if not self._send_msg_func:
            log.warning('no msg func set')
            return

        await self._send_msg_func(msg)

    async def process_message(self, message):
        prompter = self._prompter
        attempt = message.content.strip()
        prompter.attempt_buffer.append(attempt)

    async def on_enter_set_channel(self, channel):
        print(f'Setting active channel to: {channel}')
        self.active_channel = channel
        self._send_msg_func = channel.send

        await self.log(f'Active Channel Set: {channel}')
        await self.to_select_question()

    async def on_enter_stop(self):
        print(f'Tasks: {self.machine.async_tasks}')
        await self.log(f'Bot stopped')

    async def on_enter_select_question(self):
        print("on_enter_select_question")
        prompter = self._prompter

        if prompter.has_prompts():
            prompter.next_prompt()
            await self.to_announce_question()
        else:
            await self.to_announce_results()

    async def on_enter_announce_question(self):
        prompter = self._prompter
        question = prompter.current_prompt['question']
        msg = f'=======\nQuestion is:\n```\n{question}\n```'

        await self.send_msg(msg)
        await self.to_wait_for_answers()

    async def on_enter_wait_for_answers(self):
        print("on_enter_wait_for_answers")

        # TODO:
        # - minimum timeout (i.e 30 seconds)
        # - until answer with "high enough" damerauLevenshtein similarity
        # - maximum timeout (minutes?)

        await asyncio.sleep(10)

        print(f'Tasks: {self.machine.async_tasks}')
        await self.to_checking_answers()

    async def on_enter_checking_answers(self):
        prompter = self._prompter

        correct = prompter.current_prompt["answer"]
        output = [
            f'Correct Answer: "{correct}"',
            "Attempts:",

        ]
        for attempt in prompter.attempt_buffer:
            score = prompter.score(attempt)
            score = round(score, 4)
            output.append(
                f'\t{score}\t"{attempt}"'
            )
        await self.send_msg('\n'.join(output))

    async def on_enter_decide_winner(self):
        """

        i.e.
            official answer: "The RMS Titanic"

            player_one: "Titanic"     (0.4666 damerauLevenshtein)
            player_two: "The Titanic" (0.7333 damerauLevenshtein)

            official answer: "Kevin Mitnick"

            player_one:   "kev"     (0.2307 damerauLevenshtein)
            player_two:   "Kevin"   (0.3846 damerauLevenshtein)
            player_three: "Mitnick" (0.5384 damerauLevenshtein)


        I think it may be most fun to have an announcer making all decisions, with TriviaBot only stopping
        the timer early when a score of high enough value is reached (>=0.9).

        But then after that still just displaying a list to everyone of the close-ish answers.
        The list should always be in order or received (not sorted by damerauLevenshtein)


        Anyway, After displaying some sort of message representing the dilemma,
        Trivia Bot should pause on this state, and let a moderator issue a command such as:

        !winner $username
        !skip
        !vote
        """

    async def on_enter_vote_for_winner(self):
        """
        TriviaBot will post a series of messages representing each of the possible "winners"
        Everyone can vote by attaching an emoji to each post.

        After a timeout it shall enter "gather_vote_results" state or something
        """

    async def on_enter_announce_results(self):
        """
        This 'self.stop()' is somewhat of a placeholder
        However, Tribibot should pause here to allow confirmation via some sort of a command
        """
        await self.stop()


if __name__ == '__main__':
    logging.basicConfig(level='INFO')

    prompter = Prompter()
    prompter.current_prompt = {
        'question': 'this is a question',
        'answer': 'hello world',
    }
