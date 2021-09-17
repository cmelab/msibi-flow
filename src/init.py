#!/usr/bin/env python
"""Initialize the project's data space.

Iterates over all defined state points and initializes
the associated job workspace directories.
The result of running this file is the creation of a signac workspace:
    - signac.rc file containing the project name
    - signac_statepoints.json summary for the entire workspace
    - workspace/ directory that contains a sub-directory of every individual statepoint
    - signac_statepoints.json within each individual statepoint sub-directory.
"""

import signac
import logging
from collections import OrderedDict
from itertools import product
import numpy as np

def get_parameters():
    '''
    Parameters:
    -----------
    '''
    parameters = OrderedDict()
    parameters["potential_cutoff"] = [5.0]
    parameters["num_rdf_points"] = [101]
    parameters["num_rdf_frames"] = [5]
    parameters["smooth_rdf"] = [True]
    parameters["rdf_exclude_bonded"] = [False]
    parameters["r_switch"] = [None]
    parameters["integrator"] = []
    parameters["integrator_kwargs"] = []
    parameters["dt"] = [0.001]
    parameters["gsd_period"] = []
    parameters["initial_potential"] = []
    parameters["iterations"] = [20]
    parameters["n_steps"] = [1e6]

    parameters["states"] = [
                [{}, {}, {}],
            ]
    parameters["pairs"] = [
                [{}, {}, {}],
            ]
    parameters["bonds"] = [
                [{}, {}, {}],
            ]
    parameters["angles"] = [
                [{}, {}, {}],
            ]
    return list(parameters.keys()), list(product(*parameters.values()))

def main():
    project = signac.init_project("project")
    param_names, param_combinations = get_parameters()
    # Create the generate jobs
    for params in param_combinations:
        parent_statepoint = dict(zip(param_names, params))
        parent_job = project.open_job(parent_statepoint)
        parent_job.init()

    project.write_statepoints()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
