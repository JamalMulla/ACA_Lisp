import json
import math
import random
import time

from dataclasses import dataclass
import operator
from subprocess import Popen, PIPE
import os


POPULATION = 100
NUM_GENES = 39
GENERATIONS = 50


@dataclass(unsafe_hash=True)
class Individual:
    '''Class for keeping track of an individual in a population'''
    DNA: list
    fitness: float


def get_params():
    with open('params.json') as json_file:
        data = json.load(json_file)
    return data['parameters']

def get_param_name_from_params(params, index):
    keys = list(params[index].keys())
    return "-" + keys[0]



#DNA Structure
# Array where each element corresponds to the element in the json. Flattened
def dna_to_options(DNA, params):
    options_string = ""
    i = 0
    for index, e in enumerate(params):
        value = list(e.values())[0]
        if isinstance(value, dict):
            p = get_param_name_from_params(params, index) + " "
            for v in value:
                i+=1
                p += str(value.get(v)[DNA[i] % len(value.get(v)) ]) + ":"
            p = p[:-1]
            options_string += p + " "
        else:
            options_string += get_param_name_from_params(params, index) + " " + str(value[DNA[i] % len(value)] ) + " "
            i+=1

    return options_string


def create_individual(empty=False):
    if empty:
        DNA = []
    else:
        DNA = [random.randrange(0, 15) for _ in range(NUM_GENES)]
    return Individual(DNA, random.randint(100, 10000000))

def create_population():
    return [create_individual() for _ in range(POPULATION)]

def selection(generation):
    keyfun = operator.attrgetter("fitness")
    generation.sort(key=keyfun)
    topHalf = generation[:len(generation)//2]
    return topHalf

def pair(generation):
    newPopulation = []
    for first, second in zip(generation, generation[1:]):
        child1, child2 = mate(first, second)
        newPopulation.append(child1)
        newPopulation.append(child2)
    child1, child2 = mate(generation[0], generation[len(generation) - 1])
    newPopulation.append(child1)
    newPopulation.append(child2)
    return newPopulation

def mate(parent1, parent2):
    point1 = 10
    point2 = 30
    child1 = create_individual(empty=True)
    child2 = create_individual(empty=True)
    p1DNA = parent1.DNA
    p2DNA = parent2.DNA
    p1sec1 = p1DNA[:point1]
    p1sec2 = p1DNA[point1:point2]
    p1sec3 = p1DNA[point2:NUM_GENES]

    p2sec1 = p2DNA[:point1]
    p2sec2 = p2DNA[point1:point2]
    p2sec3 = p2DNA[point2:NUM_GENES]

    child1.DNA = mutate(p1sec1 + p2sec2 + p1sec3)
    child2.DNA = mutate(p2sec1 + p1sec2 + p2sec3)

    return child1, child2

def mutate(dna):
    dna = [int(round(x+random.uniform(-1, 1))) for x in dna]
    return dna

def get_top_from_pop(generation):
    return selection(generation)[0]


def parse_output(output):
    lines = output.split("\n")
    res = 0
    for line in lines:
        if "total_power_per_cycle_cc1" in line:
            parts = line.split()
            for part in parts:
                try:
                    res = float(part)
                    if res <= 100000:
                        res = math.inf
                    break
                except ValueError:
                    pass
        if res != 0:
            break
    return res

def run_generation(generation, params):


    running_procs = []
    results = {}

    for i in generation:
        my_env = os.environ.copy()
        my_env["SSFLAGS"] = dna_to_options(i.DNA, params)
        proc = Popen(['./run-wattch'], stdout=PIPE, stderr=PIPE, env=my_env)
        results[proc.pid] = [i, math.inf]
        running_procs.append(proc)

    while running_procs:
        for proc in running_procs:
            retcode = proc.poll()
            if retcode is not None:  # Process finished.
                running_procs.remove(proc)
                break
            else:  # No process is done, wait a bit and check again.
                time.sleep(.5)
                continue

        # Here, `proc` has finished with return code `retcode`
        if retcode != 0:
            """Error handling."""
            results[proc.pid][1] = math.inf
        else:
            #results[proc.pid][1] =
            results[proc.pid][1] = parse_output(proc.stdout.read())
    for k in results:
        res = results[k]
        generation[res[0]].fitness = res[1]

    return generation

if __name__ == '__main__':
    params = get_params()

    # DNA = [0, 10, 4, 4, 1, 22, 3, 4, 2, 3, 1, 0, 2, 1, 3, 2, 0, 2, 2, 2, 1, 9, 1, 0, 0, 1, 1, 2, 1, 1, 0, 0, 0, 0, 0,
    #        0, 2, 1, 2]
    #dna_to_options(DNA, params)
    pop = create_population()

    for i in range(GENERATIONS):
        pop = run_generation(pop, params)
        topHalf = selection(pop)
        pop = pair(topHalf)

        top = get_top_from_pop(pop)
        print(dna_to_options(top.DNA, params), top.fitness)

    # for individual in create_population():
    #     print(dna_to_options(individual.DNA, params))
    #print(dna_to_options(create_individual(), params))