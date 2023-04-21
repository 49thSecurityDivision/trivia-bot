import discord
from discord.ext import commands
import asyncio
import time
from operator import itemgetter

with open(".env") as f:
    TOKEN = f.read()

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='!', intents=intents)

scores = {}
questions = []
answers = []

with open('questions.txt', 'r') as file:
    lines = [line.rstrip() for line in file]
    for i in lines:
        if not i.split(' ')[0] == 'Answer':
            questions.append(' '.join(i.split(' ')[:1]))
        else:
            answers.append(' '.join(i.split(' ')[:1]))

current_question = None
question_start_time = None
quiz_channel = None
question_num = 0

async def progress_questions():
    global current_question, question_start_time
    while True:
        if quiz_channel and (not current_question or (time.time() - question_start_time) >= 30):
            if len(questions) == 0:
                await quiz_channel.send("No more questions available.")
                break

            current_question, answer = questions.pop(0)
            question_start_time = time.time()
            await quiz_channel.send(f"Question: {current_question}")

        await asyncio.sleep(1)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    bot.loop.create_task(progress_questions())

@bot.command(name='start')
async def start_quiz(ctx):
    global quiz_channel
    quiz_channel = ctx.channel
    await ctx.send("Starting quiz. Questions will be posted every 30 seconds.")

@bot.event
async def on_message(message):
    global current_question, question_start_time, question_num
    if message.author == bot.user or not current_question:
        return

    if message.content.strip().lower() == answers[question_num]:
        time_elapsed = time.time() - question_start_time
        score = max(1000 - 25 * time_elapsed, 0)

        user_id = message.author.id
        if user_id not in scores:
            scores[user_id] = {'name': str(message.author), 'score': 0}
        scores[user_id]['score'] += score

        await message.channel.send(f"{message.author.mention} answered correctly and earned {score:.0f} points! Total score: {scores[user_id]['score']:.0f}")
        current_question = None
        question_start_time = None
        question_num = question_num + 1

    await bot.process_commands(message)

@bot.command(name='score')
async def show_score(ctx):
    user_id = ctx.author.id
    if user_id not in scores:
        await ctx.send(f"{ctx.author.mention}, you haven't answered any questions yet.")
    else:
        await ctx.send(f"{ctx.author.mention}, your score is {scores[user_id]['score']:.0f} points.")

@bot.command(name='leaderboard')
async def show_leaderboard(ctx):
    sorted_scores = sorted(scores.values(), key=itemgetter('score'), reverse=True)[:10]
    if not sorted_scores:
        await ctx.send("No scores available.")
        return

    leaderboard = "🏆 Leaderboard:\n\n"
    for i, entry in enumerate(sorted_scores, start=1):
        leaderboard += f"{i}. {entry['name']} - {entry['score']:.0f} points\n"

    await ctx.send(leaderboard)

bot.run(TOKEN)
