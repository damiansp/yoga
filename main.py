#!/usr/bin/env python3

# main.py
# usage
#   main.py week [time_in_mins] [include_earlier]
#
#   week: week in course
#   time_in_mins: (int) total time of yoga session (defaults to 30)
#   include_earlier: (bool) if true, randomly chooses from all weks up to,
#     {week}, weighted more heavily toward recent weeks. (defaults to False)
import json
import os
import sys
from time import sleep

import numpy as np


WEEKLY = 'schedules/weekly'
ASANAS = 'asanas'


def main(args):
    week, total_time = args
    print(f'Starting program for week {week}\nTotal time {total_time / 60} min')
    asana_list = load_weekly_schedule(week)
    candidate_asanas = load_all_asanas(asana_list)
    candidate_asanas = [Asana(asana) for asana in candidate_asanas]
    asanas = generate_lesson(candidate_asanas, total_time)
    lesson = Lesson(asanas)
    lesson.begin()
    

# TODO: update using parseargs
def parse():
    if len(sys.argv) < 2:
        print('usage: main.py week [time_in_mins] [include_earlier]')
        sys.exit()
    week = int(sys.argv[1])
    total_time = 30 * 60
    include_earlier = False
    if len(sys.argv) > 2:
        total_time = float(sys.argv[2]) * 60
    if len(sys.argv) > 3:
        include_earlier = True if sys.argv[3].lower() == "true" else False
    if include_earlier:
        probs = np.array(range(1, week + 1))
        probs = probs / probs.sum()
        week = np.random.choice(range(1, week + 1), 1, p=probs)
    return week, total_time


def load_weekly_schedule(week):
    schedules = [f for f in os.listdir(WEEKLY) if f.endswith('.json')]
    for schedule in schedules:
        week_str = schedule.replace('weekly_', '').replace('.json', '')
        weeks = [int(x) for x in week_str.split('_')]
        if weeks[0] <= week <= weeks[1]:
            with open(f'{WEEKLY}/{schedule}', 'r') as f:
                asana_list = json.load(f)
            return asana_list
    print('Schedule not found')
    sys.exit()


def load_all_asanas(asana_list):
    asana_objs = []
    for asana in asana_list:
        try:
            with open(f'{ASANAS}/{asana}.json', 'r') as f:
                asana_objs.append(json.load(f))
        except FileNotFoundError:
            print(f'No json file for {asana}')
            sys.exit()
        except json.decoder.JSONDecodeError as e:
            print(f'Formatting error in {asana}.json\n{e}')
            sys.exit()
    return asana_objs

        
class Asana:
    def __init__(self, asana_obj):
        self.name = asana_obj['asana']
        self.hindi = asana_obj['hindi']
        self.english = asana_obj['english']
        self.images = asana_obj['images']
        self.min_time = asana_obj['minTime']
        self.max_time = asana_obj['maxTime']
        self.do_both_sides = asana_obj['doBothSides']
        self.time_per_side = int(
            round(np.random.uniform(self.min_time, self.max_time)))
        self.total_time = (2 * self.time_per_side if self.do_both_sides
                           else self.time_per_side)

    def __str__(self):
        return self.name

    def begin(self):
        print(f'{self.name}: {self.english} '
              f'({standardize_time(self.time_per_side)}; '
              f'images: {", ".join([str(x) for x in self.images])})')
        say(f'{self.english} for {standardize_time(self.time_per_side)}')
        
    def switch_sides(self):
        if self.do_both_sides:
            print('other side')
            say('other side')
        else:
            raise ValueError(
                f'{self.name} does not have left and right versions')

    @property
    def time(self):
        return self.total_time


def say(text):
    os.system(f'say {text}')


def standardize_time(time_in_s):
    if time_in_s < 60:
        return f'{time_in_s} seconds'
    minutes, seconds = time_in_s // 60, time_in_s % 60
    minutes = f'{minutes} minute%s' % ('' if minutes == 1 else 's')
    seconds = '' if seconds == 0 else f' and {seconds} seconds'
    return f'{minutes}{seconds}'


def generate_lesson(candidate_asanas, lesson_time):
    # For each lesson, if time is not sufficient for all asanas, do a random
    # subset that will fit in the time allowed, but maintain the progression
    # order
    elapsed_time = candidate_asanas[-1].time
    n = len(candidate_asanas)
    asanas = [None] * n
    # Automatically add savasana
    asanas[-1] = candidate_asanas[-1]
    indices = np.array(range(n - 1))
    np.random.shuffle(indices)
    indices = list(indices)
    while indices:
        i = indices.pop()
        next_asana = candidate_asanas[i]
        asana_time = next_asana.time
        if elapsed_time + asana_time > lesson_time:
            break
        asanas[i] = candidate_asanas[i]
        elapsed_time += asana_time
    asanas = [a for a in asanas if a is not None]
    return asanas


class Lesson:
    def __init__(self, asanas):
        self.asanas = asanas

    def begin(self):
        print('Beginning lesson...')
        say('Beginning the lesson.')
        sleep(5)
        for asana in self.asanas:
            do_both_sides = asana.do_both_sides
            time = asana.time_per_side
            asana.begin()
            sleep(time)
            if do_both_sides:
                asana.switch_sides()
                sleep(time)
        say('namaste')


if __name__ == '__main__':
    args = parse()
    main(args)
