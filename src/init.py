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

def get_parameters():
    '''Use the listed parameters below to set up
    your MSIBI instructions.

    '''
    parameters = OrderedDict()
    parameters["head_correction"] = ["linear"]
    parameters["smooth"] = [True] # Whether or not to smooth the distributions
    parameters["integrator"] = ["hoomd.md.integrate.nvt"] # Hoomd integrator type
    parameters["integrator_kwargs"] = [{"tau": 0.01}] # dict of integrator kwargs
    parameters["nlist"] = ["hoomd.md.nlist.cell"]
    parameters["nlist_exclusions"] = [["1-2", "1-3"]]
    parameters["dt"] = [0.0001]
    parameters["gsd_period"] = [50e3] # Num of steps between gsd snapshots
    parameters["iterations"] = [20, 60] # Num of MSIBI iterations to perform
    parameters["state_alphas"] = [
            [0.1, 0.1, 0.1, 0.1],
            [0.2, 0.2, 0.1, 0.2],
            [0.3, 0.3, 0.1, 0.3],
            [0.5, 0.5, 0.1, 0.5],
            [1, 1, 0.25, 1],
            [1, 1, 0.1, 1],
    ]
    parameters["n_steps"] = [
            #5e5,
            1e6,
            #5e6,
            #1e7
    ]
    parameters["optimize"]  = ["pairs"] # Choose which potential to optimize

    # These parameters below are only needed when optimizing pair potentials
    parameters["rdf_exclude_bonded"] = [True] # Exclude pairs on same molecule
    parameters["r_switch"] = [None] # Distance value to apply tail correction

    # Add state points to use during MSIBI
    parameters["states"] = [
            # Evenly Weighted, with 1.0
        [
            {"name":"A",
            "kT":6.37,
            "target_trajectory":"1.27den-6.37kT-ua.gsd",
            "max_frames": 20,
            "alpha":1.0,
            "exclude_bonded": True
            },

            {"name":"B",
            "kT":4.2,
            "target_trajectory":"1.27den-4.2kT-ua.gsd",
            "max_frames": 20,
            "alpha":1.0,
            "exclude_bonded": True
            },

            {"name":"C",
            "kT":6.5,
            "target_trajectory":"single-chain.gsd",
            "max_frames": 200,
            "alpha":1.0,
            "exclude_bonded": False
            },

            {"name":"D",
            "kT":2.77,
            "target_trajectory":"1.40den-2.77kT-ua.gsd",
            "max_frames": 20,
            "alpha":1.0,
            "exclude_bonded": True
            },
        ],

    ]

    # Add parameters needed to create Pair objects
    parameters["pairs"] = [
        [
            {"type1":"E",
             "type2":"E",
             "form": "table",
             "kwargs": {
                 "n_points": 101,
                 "epsilon": 1.5,
                 "sigma": 2,
                 "r_max": 5.0,
                 "r_min": 1e-3
              }
             },

            {"type1":"E",
             "type2":"K",
             "form": "table",
             "kwargs": {
                 "n_points": 101,
                 "epsilon": 1.5,
                 "sigma": 2,
                 "r_max": 5.0,
                 "r_min": 1e-3
              }
             },

            {"type1":"K",
             "type2":"K",
             "form": "table",
             "kwargs": {
                 "n_points": 101,
                 "epsilon": 1.5,
                 "sigma": 2,
                 "r_max": 5.0,
                 "r_min": 1e-3
              }
             },
        ],

	]

    # Add parameters needed to create Bond and Angle objects
    parameters["bonds"] = [
            [
                {"type1":"E",
                 "type2":"K",
                 "form": "file",
                 "kwargs": {"file_path": "E-K_smoothed.txt"}
                 },

                {"type1":"K",
                 "type2":"K",
                 "form": "file",
                 "kwargs": {"file_path": "K-K_smoothed.txt"}
                 }
            ]
    ]

    parameters["angles"] = [
            [
                {"type1":"E",
                "type2":"K",
                "type3": "K",
                "form": "file",
                "kwargs": {"file_path": "E-K-K_smoothed-1.0.txt"}
                },

                {"type1":"K",
                "type2":"E",
                "type3": "K",
                "form": "file",
                "kwargs": {"file_path": "K-E-K_smoothed.txt"}
                },
            ]
    ]

    parameters["dihedrals"] = [

                None,
            [
                {"type1":"E",
                "type2":"K",
                "type3": "K",
                "type4": "E",
                "form": "harmonic",
                "kwargs": {"phi0": 0, "k": "20", "d": -1, "n":1}
                },

                {"type1":"K",
                "type2":"E",
                "type3": "K",
                "type4": "K",
                "form": "harmonic",
                "kwargs": {"phi0": 0, "k": "13", "d": -1, "n":1}
                },

            ]
    ]
    return list(parameters.keys()), list(product(*parameters.values()))

def main():
    project = signac.init_project("msibi-chain")
    param_names, param_combinations = get_parameters()
    # Create the generate jobs
    for params in param_combinations:
        parent_statepoint = dict(zip(param_names, params))
        parent_job = project.open_job(parent_statepoint)
        parent_job.init()
        parent_job.doc.setdefault("integrator_kwargs", parent_job.sp.integrator_kwargs)
    project.write_statepoints()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
