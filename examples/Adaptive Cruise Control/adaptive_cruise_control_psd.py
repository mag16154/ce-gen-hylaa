'''
Adaptive cruise control, with dynamics:

vf' == 0
s' == vf - v
v' == a - k * v
a' == -2 * a - 2 * (v - vf)
'''

import math
import numpy as np
from hylaa.hybrid_automaton import LinearHybridAutomaton, HyperRectangle, LinearConstraint
from hylaa.star import init_hr_to_star
from hylaa.engine import HylaaSettings, HylaaEngine
from hylaa.containers import PlotSettings
from hylaa.pv_container import PVObject
from hylaa.timerutil import Timers
from hylaa.simutil import  compute_simulation
import matplotlib.pyplot as plt


def define_ha(settings, usafe_r):
    # x' = Ax + Bu + c
    '''make the hybrid automaton and return it'''

    k = -0.0025
    # k = -0.015
    ha = LinearHybridAutomaton()
    ha.variables = ["s", "v", "vf", "a", "t"]

    loc1 = ha.new_mode('loc1')

    loc1.a_matrix = np.array([[0, -1, 1, 0, 0], [0, k, 0, 1, 0], [0, 0, 0, 0, 0], [0, -2, 2, -2, 0], [0, 0, 0, 0, 0]])
    loc1.c_vector = np.array([0, 0, 0, 0, 1], dtype=float)

    error = ha.new_mode('_error')
    error.is_error = True

    trans = ha.new_transition(loc1, error)

    usafe_set_constraint_list = []
    if usafe_r is None:
        usafe_set_constraint_list.append(LinearConstraint([1, 0, 0, 0, 0], 0.05))
        usafe_set_constraint_list.append(LinearConstraint([0, -1, 0, 0, 0], -68))
        # usafe_set_constraint_list.append(LinearConstraint([-1, 0, 0, 0], -0.03))
    else:
        usafe_star = init_hr_to_star(settings, usafe_r, ha.modes['_error'])
        for constraint in usafe_star.constraint_list:
            usafe_set_constraint_list.append(constraint)

    for constraint in usafe_set_constraint_list:
        trans.condition_list.append(constraint)

    return ha, usafe_set_constraint_list


def define_init_states(ha, init_r):
    '''returns a list of (mode, HyperRectangle)'''
    # Variable ordering: [x, y]
    rv = []
    rv.append((ha.modes['loc1'], init_r))

    return rv


def define_settings():
    'get the hylaa settings object'
    plot_settings = PlotSettings()
    plot_settings.plot_mode = PlotSettings.PLOT_IMAGE
    plot_settings.xdim = 0
    plot_settings.ydim = 1

    s = HylaaSettings(step=0.2, max_time=20.0, plot_settings=plot_settings)
    s.stop_when_error_reachable = False
    
    return s


def run_hylaa(settings, init_r, usafe_r):

    'Runs hylaa with the given settings, returning the HylaaResult object.'

    ha, usafe_set_constraint_list = define_ha(settings, usafe_r)
    init = define_init_states(ha, init_r)

    engine = HylaaEngine(ha, settings)
    reach_tree = engine.run(init)

    return PVObject(len(ha.variables), usafe_set_constraint_list, reach_tree)


def compute_simulation_mt(longest_ce, deepest_ce):

    a_matrix = np.array([[0, -1, 1, 0, 0], [0, -0.02, 0, 1, 0], [0, 0, 0, 0, 0], [0, -2, 2, -2, 0], [0, 0, 0, 0, 0]])
    c_vector = np.array([0, 0, 0, 0, 1], dtype=float)
    longest_ce_simulation = compute_simulation(longest_ce, a_matrix, c_vector, 0.2, 100)

    deepest_ce_simulation = compute_simulation(deepest_ce, a_matrix, c_vector, 0.2, 100)

    with open("simulation", 'w') as f:
        f.write('longest_simulation = [')
        t = 0.0
        for point in longest_ce_simulation:
            f.write('{},{};\n'.format(str(point[0]), str(point[1])))
            t = t + 0.2
        f.write(']')
        f.write('\n**************************************\n')
        f.write('deepest_simulation = [')
        t = 0.0
        for point in deepest_ce_simulation:
            f.write('{},{};\n'.format(point[0], str(point[1])))
            t = t + 0.2
            f.write(']')


if __name__ == '__main__':
    settings = define_settings()
    init_r = HyperRectangle([(0.1, 0.5), (63, 77), (65, 65), (0, 0), (0, 0)])
    # init_r = HyperRectangle([(100, 120), (55, 65), (60, 60), (0, 0)])
    pv_object = run_hylaa(settings, init_r, None)

    direction = np.zeros(len(init_r.dims))
    longest_ce = pv_object.compute_longest_ce()
    depth_direction = np.identity(len(init_r.dims))
    deepest_ce = pv_object.compute_deepest_ce(depth_direction[1])
    Timers.print_stats()