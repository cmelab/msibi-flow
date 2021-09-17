"""Define the project's workflow logic and operation functions.

Execute this script directly from the command line, to view your project's
status, execute operations and submit them to a cluster. See also:

    $ python src/project.py --help
"""
import signac
from flow import FlowProject, directives
from flow.environment import DefaultSlurmEnvironment
from flow.environments.xsede import BridgesEnvironment, CometEnvironment

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
@MyProject.label
def completed(job):
    return job.doc.get("done")


@directives(executable="python -u")
@directives(ngpu=1)
@MyProject.operation
@MyProject.post(completed)
def optimize(job):
    from msibi import MSIBI, State, Pair, Bond, Angle, mie, morse
    import logging

    with job:
        logging.info("Setting up MSIBI optimizer...")
        opt = MSIBI(
                pot_cutoff=job.sp.potential_cutoff,
                rdf_cutoff=job.sp.potential_cutoff,
                n_rdf_points=job.sp.num_rdf_points,
                max_frames=job.sp.num_rdf_frames,
                smooth_rdfs=job.sp.smooth_rdf,
                rdf_exclude_bonded=job.sp.rdf_exclude_bonded,
                verbose=False
                )
        logging.info("Creating State objects...")
        for state in job.states:
            opt.add_state(
                    State(
                    name=state["name"],
                    kT=state["kT"],
                    traj_file=state["target_trajectory"],
                    alpha=state["alpha"]
                )
            )

        logging.info("Creating Pair objects...")
        for pair in job.pairs:
            if "potential" in pair.keys():
                potential=pair["potential"]
            else:
                potential=job.sp.initial_potential
            opt.add_pair(
                    Pair(
                        type1=pair["type1"],
                        type2=pair["type2"],
                        potential=potential
                    )
                )

        if job.sp.bonds is not None:
            logging.info("Creating Bond objects...")
            for bond in job.bonds:
                opt.add_bond(
                        Bond(
                            type1=bond["type1"],
                            type2=bond["type2"],
                            k=bond["k"],
                            r0=bond["r0"]
                        )
                    )
        
        if job.sp.angles is not None:
            logging.info("Creating Angle objects...")
            for angle in job.angles:
                opt.add_angle(
                        Angle(
                            type1=angle["type1"],
                            type2=angle["type2"],
                            type3=angle["type3"],
                            k=angle["k"],
                            theta=angle["theta0"]
                        )
                    )

        opt.optimize(
                n_iterations=job.sp.iterations,
                engine="hoomd",
                n_steps=job.sp.n_steps,
                integrator=job.sp.integrator,
                integrator_kwargs=job.sp.integrator_kwargs,
                dt=job.sp.dt,
                gsd_period=job.sp.gsd_period
                )

        job.doc["done"] = True


if __name__ == "__main__":
    MyProject().main()
