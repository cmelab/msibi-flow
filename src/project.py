"""Define the project's workflow logic and operation functions.

Execute this script directly from the command line, to view your project's
status, execute operations and submit them to a cluster. See also:

    $ python src/project.py --help

"""

import signac
from flow import FlowProject, directives
from flow.environment import DefaultSlurmEnvironment
from flow.environments.xsede import Bridges2Environment
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
@MyProject.label
def completed(job):
    return job.doc.get("done")

def get_file(job, file_name):
    return os.path.abspath(os.path.join(job.ws, "..", "..", file_name))

@directives(executable="python -u")
@directives(ngpu=1)
@MyProject.operation
@MyProject.post(completed)
def optimize(job):
    from msibi import MSIBI, State, Pair, Bond, Angle, Dihedral
    import logging

    with job:
        job.doc["done"] = False

        print("Setting up MSIBI optimizer...")
        opt = MSIBI(
            integrator=job.sp.integrator,
            integrator_kwargs=job.doc.integrator_kwargs,
            nlist=job.sp.nlist,
            nlist_exclusions=job.sp.nlist_exclusions,
            dt=job.sp.dt,
            gsd_period=job.sp.gsd_period,
            n_steps=job.sp.n_steps,
        )

        print("Creating State objects...")
        for idx, state in enumerate(job.sp.states):
            alpha = job.sp.state_alphas[idx]
            opt.add_state(
                State(
                    name=state["name"],
                    kT=state["kT"],
                    traj_file=get_file(
                        job,
                        f"msibi-state-point-files/{state['target_trajectory']}"
                    ),
                    max_frames=state["max_frames"],
                    target_frames=state["target_frames"],
                    alpha=alpha,
                    exclude_bonded=state["exclude_bonded"],
					_dir=job.ws
                )
            )

        print("Creating Pair objects...")
        for pair in job.sp.pairs:
            _pair = Pair(
                        type1=pair["type1"],
                        type2=pair["type2"],
                        head_correction_form = job.sp.head_correction
                    )

            if pair["form"] == "table":
                _pair.set_table_potential(**pair["kwargs"])
            elif pair["form"] == "file":
                job.doc.pair_form = "file"
                file_path = get_file(job, pair["kwargs"]["file_path"])
                _pair.set_from_file(file_path=file_path)

            opt.add_pair(_pair)

        if job.sp.bonds is not None:
            print("Creating Bond objects...")
            for bond in job.sp.bonds:
                _bond = Bond(
                        type1=bond["type1"],
                        type2=bond["type2"],
                        head_correction_form=job.sp.head_correction
                )

                if bond["form"] == "file":
                    file_path = get_file(job, bond["kwargs"]["file_path"])
                    _bond.set_from_file(file_path=file_path)
                elif bond["form"] == "quadratic":
                    _bond.set_quadratic(**bond["kwargs"])

                opt.add_bond(_bond)

        if job.sp.angles is not None:
            print("Creating Angle objects...")
            for angle in job.sp.angles:
                _angle = Angle(
                        type1=angle["type1"],
                        type2=angle["type2"],
                        type3=angle["type3"],
                        head_correction_form=job.sp.head_correction
                )

                if angle["form"] == "file":
                    file_path = get_file(job, angle["kwargs"]["file_path"])
                    _angle.set_from_file(file_path)
                elif angle["form"] == "harmonic":
                    _angle.set_harmonic(**angle["kwargs"])

                opt.add_angle(_angle)

        if job.sp.dihedrals is not None:
            print("Creating Dihedral objects...")
            for dihedral in job.sp.dihedrals:
                _dihedral = Dihedral(
                        type1=dihedral["type1"],
                        type2=dihedral["type2"],
                        type3=dihedral["type3"],
                        type4=dihedral["type4"],
                )
                if dihedral["form"] == "file":
                    file_path = get_file(job, dihedral["kwargs"]["file_path"])
                    _dihedral.set_from_file(file_path)
                elif dihedral["form"] == "harmonic":
                    _dihedral.set_harmonic(**dihedral["kwargs"])

                opt.add_dihedral(_dihedral)

        if job.sp.optimize == "bonds":
            opt.optimize_bonds(
                    n_iterations=job.sp.iterations,
                    smooth=job.sp.smooth,
                    _dir=job.ws
            )
        elif job.sp.optimize == "angles":
            opt.optimize_angles(
                    n_iterations=job.sp.iterations,
                    smooth=job.sp.smooth,
                    _dir=job.ws
            )
        elif job.sp.optimize == "pairs":
            opt.optimize_pairs(
                    n_iterations=job.sp.iterations,
                    smooth_rdfs=job.sp.smooth,
                    smoothing_window=9,
                    r_switch=job.sp.r_switch,
                    _dir=job.ws
            )
        elif job.sp.optimize == "dihedrals":
            opt.optimize_dihedrals(
                    n_iterations=job.sp.iterations,
                    smooth_rdfs=job.sp.smooth,
                    _dir=job.ws
            )

        job.doc["done"] = True


if __name__ == "__main__":
    MyProject().main()
