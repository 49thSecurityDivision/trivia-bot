#!/usr/bin/env python3


import unittest

from trivia_prompter import Prompter


TEST_PROMPT = {
    'question': 'this is a test question',
    'answer': 'hello world',
}


class TestPrompter(unittest.TestCase):

    def setUp(self):
        self.prompter = Prompter()

    def tearDown(self):
        del self.prompter

    ##################################
    # String Distance Function Tests #
    ##################################
    # The following tests for normalization of answers
    # We don't want formatting to

    def test_string_distance(self):
        distance = self.prompter.string_distance
        correct = "hello world"

        value = distance(correct, "hello world")
        self.assertEqual(value, 1.0)

    def test_distance_whitespace(self):
        distance = self.prompter.string_distance
        correct = "hello world"

        # Leading/Trailing Whitespace
        value = distance(correct, " hello world\n")
        self.assertEqual(value, 1.0)

        # Double Space
        value = distance(correct, "hello  world")
        self.assertEqual(value, 1.0)

    def test_distance_case_sensitivity(self):
        distance = self.prompter.string_distance
        correct = "hello world"

        value = distance(correct, "Hello World")
        self.assertEqual(value, 1.0)

        # While we maybe won't normalize the "answer" as much,
        # still should be lowercasing both 'correct' and 'attempt'
        value = distance(correct.upper(), "Hello World")
        self.assertEqual(value, 1.0)

        value = distance(correct, "HELLO WORLD")
        self.assertEqual(value, 1.0)

    def test_distance_punctuation(self):
        raise NotImplemented

    #############
    # xyz Tests #
    #############
