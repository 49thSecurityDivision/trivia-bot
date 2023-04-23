SHELL	:= /bin/bash

test:
	python3 -m unittest discover --verbose -s trivia_prompter 
