#!/usr/bin/env python3

# main.py
# usage
#   main.py week [time_in_mins] [include_earlier="true"] [corpse=False]
#
#   week: week in course
#   time_in_mins: (int) total time of yoga session (defaults to 30)
#   include_earlier: (bool) if true, randomly chooses from all weks up to,
#     {week}, weighted more heavily toward recent weeks. (defaults to False)
import argparse
import json
import os
import sys
from time import sleep, time

import numpy as np
from PIL import Image


WEEKLY = 'schedules/weekly'
ASANAS = 'asanas'
IMG = 'images'


def main(args):
    week, total_time, do_corpse, max_per = parse_args(args)
    asana_list = load_weekly_schedule(week)
    candidate_asanas = load_all_asanas(asana_list)
    candidate_asanas = [Asana(asana, max_per) for asana in candidate_asanas]
    asanas = generate_lesson(candidate_asanas, total_time, do_corpse)
    lesson = Lesson(asanas)
    lesson.begin()
    

def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('-w', '--week', help='maximum week to select', type=int)
    parser.add_argument(
        '-t', '--time', help='time of practice in minutes', type=int, default=20)
    parser.add_argument(
        '-e', '--exact', help='run only the specified week', action='store_true')
    parser.add_argument(
        '-c', '--nocorpse', help='omit corpse pose', action='store_true')
    parser.add_argument('-x',
                        '--max_per',
                        help='maximum minutes per asana',
                        type=int,
                        default=np.inf)
    args = parser.parse_args()
    # change times to seconds
    args.time *= 60.
    args.max_per *= 60.
    if not args.exact:
        probs = np.array([0.85**i for i in range(args.week)][::-1])
        probs = probs / probs.sum()
        week = np.random.choice(range(1, args.week + 1), 1, p=probs)[0]
        week = week
    do_corpse = not args.nocorpse
    args = [week, args.time, do_corpse, args.max_per]
    print('Running with args:')
    for name, val in zip(['week', 'total_time', 'do_corpse', 'max_per'], args):
        print(f'  {name:10s}: {val}')
    return args


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
    def __init__(self, asana_obj, max_per=np.inf):
        self.name = asana_obj['asana']
        if self.name == 'savasana': # max_per doesn't apply to corpse pose
            max_per = np.inf
        self.hindi = asana_obj['hindi']
        self.english = asana_obj['english']
        self.images = asana_obj['images']
        self.min_time = asana_obj['minTime']
        self.max_time = min(asana_obj['maxTime'], max_per)
        self.do_both_sides = asana_obj['doBothSides']
        self.time_per_side = int(
            round(np.random.uniform(self.min_time, self.max_time)))
        self.total_time = (2 * self.time_per_side if self.do_both_sides
                           else self.time_per_side)
        self.img = asana_obj.get('imgFile', None)

    def __str__(self):
        return self.name

    def begin(self, current_im=None):
        if current_im is not None:
            current_im.close()
        im = None
        if self.img is not None:
            try:
                im = Image.open(f'{IMG}/{self.img}')
                im.show()
            except BaseException as e:
                print(f'Failed to open {self.img}\n{e}')
        print(f'{self.name}: {self.english} '
              f'({standardize_time(self.time_per_side)}; '
              f'images: {", ".join([str(x) for x in self.images])})')
        say(f'{self.english} for {standardize_time(self.time_per_side)}')
        return im
        
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


def say(text, voice='Rishi'):
    os.system(f'say -v {voice} {text}')


def standardize_time(time_in_s):
    if time_in_s < 60:
        return f'{int(round(time_in_s))} seconds'
    minutes, seconds = int(time_in_s // 60), time_in_s % 60
    seconds = int(round(seconds))
    if seconds == 60:
        minutes += 1
        seconds = 0
    minutes = f'{minutes} minute%s' % ('' if minutes == 1 else 's')
    seconds = '' if seconds == 0 else f' and {seconds} seconds'
    return f'{minutes}{seconds}'


def generate_lesson(candidate_asanas, lesson_time, do_corpse):
    # For each lesson, if time is not sufficient for all asanas, do a random
    # subset that will fit in the time allowed, but maintain the progression
    # order
    n = len(candidate_asanas)
    asanas = [None] * n
    if do_corpse:
        # Automatically add savasana
        print('Including savasana')
        asanas[-1] = candidate_asanas[-1]
        elapsed_time = candidate_asanas[-1].time
    else:
        print('Omitting savasana')
        elapsed_time = 0
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
    # Adjust time each to make exact
    if elapsed_time !=lesson_time:
        asanas = adjust_times(asanas, lesson_time, elapsed_time)
    return asanas


def adjust_times(asanas, lesson_time, elapsed_time):
    print('Updating time each...')
    factor = lesson_time / elapsed_time
    for a in asanas:
        a.time_per_side *= factor
        a.total_time *= factor
    return asanas


class Lesson:
    def __init__(self, asanas):
        self.asanas = asanas

    def begin(self):
        say('Beginning the lesson.')
        sleep(5)
        start = time()
        im = None
        for asana in self.asanas:
            do_both_sides = asana.do_both_sides
            asana_time = asana.time_per_side
            im = asana.begin(im)
            sleep(asana_time)
            if do_both_sides:
                asana.switch_sides()
                sleep(asana_time)
            try:
                im.close()
            except:
                pass
        elapsed_time = time() - start
        say('नमस्ते', voice='Lekha')
        print('Elapsed time:', elapsed_time)


if __name__ == '__main__':
    main(sys.argv)
