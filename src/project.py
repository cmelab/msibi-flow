"""Define the project's workflow logic and operation functions.

Execute this script directly from the command line, to view your project's
status, execute operations and submit them to a cluster. See also:

    $ python src/project.py --help
"""
import signac
from flow import FlowProject, directives
from flow.environment import DefaultSlurmEnvironment
from flow.environments.xsede import BridgesEnvironment, CometEnvironment
import os

class MyProject(FlowProject):
    pass

class Borah(DefaultSlurmEnvironment):
    hostname_pattern = "borah"
    template = "borah.sh"

    @classmethod
    def add_args(cls, parser):
        parser.add_argument(
            "--partition", default="gpu", help="Specify the partition to submit to."
        )

class R2(DefaultSlurmEnvironment):
    hostname_pattern = "r2"
    template = "r2.sh"

    @classmethod
    def add_args(cls, parser):
        parser.add_argument(
            "--partition", default="gpuq", help="Specify the partition to submit to."
        )

class Fry(DefaultSlurmEnvironment):
    hostname_pattern = "fry"
    template = "fry.sh"

    @classmethod
    def add_args(cls, parser):
        parser.add_argument(
            "--partition", default="batch", help="Specify the partition to submit to."
        )

# Definition of project-related labels (classification)
def current_step(job):
    import gsd.hoomd

    if job.isfile("sim_traj.gsd"):
        with gsd.hoomd.open(job.fn("sim_traj.gsd")) as traj:
            return traj[-1].configuration.step
    return -1


@MyProject.label
def sampled(job):
    return current_step(job) >= job.doc.steps


@MyProject.label
def initialized(job):
    return job.isfile("init.mol2")


@MyProject.label
def rdf_done(job):
    try:
        if len(os.listdir(os.path.join(job.ws, 'rdf-results'))) > 0:
            return True
        else:
            return False
    except:
        return False

@MyProject.label
def msd_done(job):
    try:
        if len(os.listdir(os.path.join(job.ws, 'msd-results'))) > 0:
            return True
        else:
            return False
    except:
        return False
    

@MyProject.label
def ind_sampling_done(job):
    return job.isfile("sim_traj_equil.log")


@directives(executable="python -u")
@directives(ngpu=1)
@MyProject.operation
@MyProject.post(sampled)
def sample(job):
    from uli_init import simulate, system
    from uli_init.utils import base_units, unit_conversions
    import numpy as np
    import logging

    with job:
        logging.info("Creating system...")
        if job.sp["system_type"] != "interface":
            system = system.System(
                    molecule = job.sp['molecule'],
                    para_weight = job.sp['para_weight'],
                    monomer_sequence = job.sp['monomer_sequence'],
                    density = job.sp['density'],
                    n_compounds = job.sp['n_compounds'],
                    polymer_lengths = job.sp["polymer_lengths"],
                    system_type = job.sp["system_type"],
                    forcefield = job.sp['forcefield'],
                    sample_pdi = job.doc.sample_pdi,
                    pdi = job.sp['pdi'],
                    Mn = job.sp['Mn'],
                    Mw = job.sp['Mw'],
                    mass_dist_type = job.sp['mass_dist'],
                    remove_hydrogens = job.sp['remove_hydrogens'],
                    seed = job.sp['system_seed']
                )
            shrink_kT = job.sp['shrink_kT'] 
            shrink_steps = job.sp['shrink_steps']
            shrink_period = 500
            job.doc['num_para'] = system.para
            job.doc['num_meta'] = system.meta
            job.doc['num_compounds'] = system.n_compounds
            job.doc['polymer_lengths'] = system.polymer_lengths

        elif job.sp["system_type"] == "interface":
            slab_files = []
            ref_distances = []
            if job.doc['use_signac']:
                signac_args = []
                if isinstance(job.sp['signac_args'], list):
                    slab_1_arg = job.sp['signac_args'][0]
                    signac_args.append(slab_1_arg)
                    if len(job.sp['signac_args']) == 2:
                        slab_2_arg = job.sp['signac_args'][1]
                        signac_args.append(slab_2_args)
                elif not isinstance(job.sp['signac_args'], list):
                    signac_args.append(job.sp['signac_args'])

                project = signac.get_project(root=job.sp['signac_project'], search=True)
                for arg in signac_args:
                    if isinstance(arg, signac.core.attrdict.SyncedAttrDict): 
                        _job = list(project.find_jobs(filter=arg))[0]
                        slab_files.append(_job.fn('restart.gsd'))
                        ref_distances.append(_job.doc['ref_distance']/10)
                    elif isinstance(arg, str): # Find job using job ID
                        _job = project.open_job(id=arg)
                        slab_files.append(_job.fn('restart.gsd'))
                        ref_distances.append(_job.doc['ref_distance']/10)
            elif not job.doc['use_signac']: # Using a specified path to the .gsd file(s)
                slab_files.append(job.sp['slab_file'])
                ref_distances.append(job.sp['reference_distance'])

            if len(ref_distances) == 2:
                assert ref_distances[0] == ref_distances[1]

            system = system.Interface(slabs = slab_files,
                                        ref_distance = ref_distances[0],
                                        gap = job.sp['interface_gap'],
                                        forcefield = job.sp['forcefield'],
                                        )

            job.doc['slab_ref_distances'] = system.ref_distance
            shrink_kT = None 
            shrink_steps = None
            shrink_period = None

        system.system.save('init.mol2', overwrite=True)
        logging.info("System generated...")
        logging.info("Starting simulation...")

        simulation = simulate.Simulation(
                system,
                target_box = None,
                r_cut = job.sp["r_cut"],
                e_factor = job.sp['e_factor'],
                tau_kt = job.sp['tau_kt'],
		        tau_p = job.sp['tau_p'],
                nlist = job.sp['neighbor_list'],
                dt = job.sp['dt'],
                seed = job.sp['sim_seed'],
                auto_scale = True,
                ref_units = None,
                mode = "gpu",
                gsd_write = max([int(job.doc['steps']/100), 1]),
                log_write = max([int(job.doc['steps']/10000), 1])
                )

        logging.info("Simulation object generated...")
        job.doc['ref_energy'] = simulation.ref_energy
        job.doc['ref_distance'] = simulation.ref_distance
        job.doc['ref_mass'] = simulation.ref_mass
        job.doc['real_timestep'] = unit_conversions.convert_to_real_time(simulation.dt,
                                                    simulation.ref_energy,
                                                    simulation.ref_distance,
                                                    simulation.ref_mass)
        job.doc['time_unit'] = 'fs'
        job.doc['steps_per_frame'] = simulation.gsd_write
        job.doc['steps_per_log'] = simulation.log_write

        if job.sp['procedure'] == "quench":
            job.doc['T_SI'] = unit_conversions.kelvin_from_reduced(job.sp['kT_quench'],
                                                    simulation.ref_energy)
            job.doc['T_unit'] = 'K'
            logging.info("Beginning quench simulation...")
            simulation.quench(
                    kT = job.sp['kT_quench'],
					pressure = job.sp['pressure'],
                    n_steps = job.sp['n_steps'],
                    shrink_kT = shrink_kT,
                    shrink_steps = shrink_steps,
                    walls = job.sp['walls'],
                    shrink_period = shrink_period
                    )

        elif job.sp['procedure'] == "anneal":
            logging.info("Beginning anneal simulation...")
            if not job.sp['schedule']:
                kT_list = np.linspace(job.sp['kT_anneal'][0],
                                      job.sp['kT_anneal'][1],
                                      len(job.sp['anneal_sequence']),
                                      )
                kT_SI = [unit_conversions.kelvin_from_reduced(kT, simulation.ref_energy)
                            for kT in kT_list]
                job.doc['T_SI'] = kT_SI
                job.doc['T_unit'] = 'K'

            simulation.anneal(
                    kT_init = job.sp['kT_anneal'][0],
                    kT_final = job.sp['kT_anneal'][1],
					pressure = job.sp['pressure'],
                    step_sequence = job.sp['anneal_sequence'],
                    schedule = job.sp['schedule'],
                    shrink_kT = shrink_kT,
                    shrink_steps = shrink_steps,
                    walls = job.sp['walls'],
                    shrink_period = shrink_period 
                    )

if __name__ == "__main__":
    MyProject().main()
