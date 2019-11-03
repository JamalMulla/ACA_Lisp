import json
import math
import random
import time

from dataclasses import dataclass
import operator
from subprocess import Popen, PIPE
import os


POPULATION = 200
NUM_GENES = 39
GENERATIONS = 100


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
    return Individual(DNA, math.inf)

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



def parse_output(output):
    lines = output.splitlines()
    res = 0
    for line in lines:
        line = line.decode('utf-8')
        #print(line)
        if "total_power_cycle_cc1" in line:
            parts = line.split()
            for part in parts:
                try:
                    res = float(part)
                    if res <= 1000000:
                        res = math.inf
                    break
                except ValueError:
                    pass
        if res != 0:
            break
    if res == 0:
        res = math.inf
    #print("final res", res)
    return res

def run_generation(generation, params):
    start = time.time()
    running_procs = []
    results = {}

    for i, e in enumerate(generation):
        env = {
            **os.environ,
            "SSFLAGS": dna_to_options(e.DNA, params),
        }
        proc = Popen(['./run-wattch'], stdout=PIPE, stderr=PIPE, shell=True, env=env)

        results[proc.pid] = [i, math.inf]
        running_procs.append(proc)

    while running_procs:
        for proc in running_procs:
            retcode = proc.poll()
            if retcode is not None:  # Process finished.
                print("finished process", proc.pid)
                running_procs.remove(proc)
                break
            else:  # No process is done, wait a bit and check again.
                time.sleep(.1)
                continue

        if retcode == None:
            output, error = proc.communicate()
            results[proc.pid][1] = parse_output(output)
            #print("success:", proc.pid)
            #print("none  was retcode", "output", output, "error", error)
        else:
            # results[proc.pid][1] =
            try:
                output, error = proc.communicate()
                #print("fail:", proc.pid)
                results[proc.pid][1] =  parse_output(error)
            except ValueError:
                print("was error")
                pass


    for k in results:
        res = results[k]

        generation[res[0]].fitness = res[1]

    print("--- Took %s seconds to run generations ---" % (time.time() - start))
    return generation

def write_list_to_file(l):
    with open('results.txt', 'w') as f:
        for item in l:
            f.write("%s\n" % item)


if __name__ == '__main__':
    params = get_params()


    pop = create_population()

    results = []
    for i in range(GENERATIONS):
        start = time.time()
        print("Generation ", i)
        pop = run_generation(pop, params)
        topHalf = selection(pop)
        top = topHalf[0]
        print("top", top.fitness)
        results.append(top)
        for i in topHalf:
            print(i.fitness)

        pair_start = time.time()
        pop = pair(topHalf)
        print("--- Took %s seconds to create new population ---" % (time.time() - pair_start))
        
        print(dna_to_options(top.DNA, params), top.fitness)

        print("--- Took %s seconds in total ---" % (time.time() - start))
    write_list_to_file(results)
    # for individual in create_population():
    #     print(dna_to_options(individual.DNA, params))
    #print(dna_to_options(create_individual(), params))
