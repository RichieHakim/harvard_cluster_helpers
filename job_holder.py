"""
JOB HOLDER
RH 2024

This script is used to constrain the number of jobs that a user can have running
at one time. It is a daemon that isintended to run persistently on a small node.
It is written in pure/native Python 3 and uses the subprocess module to interact
with the SLURM.

Written to be used on Harvard's 02 and FASRC clusters.\n

Script proceeds as follows:
1. Runs squeue to get information about all jobs
2. Parses information about each job
3. Determines which jobs must be set to HOLD
4. Runs scontrol hold <job_id> to hold jobs
5. Runs scontrol release <job_id> to release jobs
6. Repeats every 5 seconds.
"""

import argparse
import subprocess
import time
import datetime
import re
import itertools
import threading
import sys

## Print to terminal
def print(*args, **kwargs):
    return __builtins__.print(*args, **kwargs, file=sys.stderr)

## Properties to get from squeue
properties = {
    'job_id': 'JobId',
    'name': 'Name',
    'state': 'State',
    'submit_time': 'SubmitTime',
    'partition': 'Partition',
    'time_limit': 'TimeLimit',
    'nodes': 'NumNodes',
    'cpus': 'NumCPUs',
    'memory': 'MinMemory',
    'time_left': 'TimeLeft',
    'priority': 'Priority',
    'node_reason': 'ReasonList',
}

def parse_args():
    parser = argparse.ArgumentParser(description="Manage job holding and releasing based on custom rules.")
    ## value_max, float, default=12
    parser.add_argument(
        "-v",
        "--value_max",
        type=float,
        default=12,
        help="Maximum value for the constraint on running jobs. This is the maximum value that 'constraint' can be before jobs are held. Default: 12.",
    )
    parser.add_argument(
        "-c",
        "--constraint",
        type=str, 
        choices=['nodes', 'cpus', 'memory', 'time_left', 'jobs', 'fairshare',],
        default='nodes',
        help="Constraint to manage jobs by. Default: 'nodes'.",
    )
    parser.add_argument(
        "-o",
        "--order_by", 
        type=str, 
        choices=list(properties.keys()),
        default="submit_time",
        help="Sort pending jobs by this property. Default: 'submit_time'.",
        )
    parser.add_argument(
        "-i",
        "--interval", 
        type=int, 
        default=5,
        help="Interval in seconds for checking and managing jobs. Default: 5.",
    )
    ## Optional args
    parser.add_argument(
        "--username", 
        type=str,
        default=None,
        help="Username for which to manage jobs. Default: current user from 'whoami'.",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60*60*24*365,
        help="Total/maximum duration in seconds to run the script. Default: 1 year.",
    )
    ## Flags
    parser.add_argument(
        "--verbose", 
        type=int,
        help="Print verbose output. Default: 0. Options: 0: No output, 1: Warnings, 2: Commands executed, 3: Debugging output.",
    )
    parser.add_argument(
        "--dry-run", 
        action='store_true',
        help="Dry run. Do not actually hold or release jobs.",
    )
    parser.add_argument(
        "--no-daemon", 
        action='store_true',
        help="Run once and exit.",
    )
    
    return parser.parse_args()



def _parse_slurm_duration(t):
    """
    Parses a slurm formatted duration string into a datetime timedelta object.\n
    Useful for TimeLimit and TimeLeft fields in squeue output.\n
    Expects format: "D-HH:MM:SS" or "HH:MM:SS" or "MM:SS" or "SS".\n
    """
    ## Handle optional days ('-')
    if '-' in t:
        days, time = t.split('-')
        days = int(days)
    else:
        days = 0
        time = t
    
    ## Handle optional hours and minutes (':')
    if ':' in time:
        hms = time.split(':')
        if len(hms) == 3:
            hours, minutes, seconds = (int(h) for h in hms)
        elif len(hms) == 2:
            minutes, seconds = (int(h) for h in hms)
            hours = 0
        else:
            raise ValueError("Invalid time format.")
    else:
        try:
            seconds = int(time)
            hours = 0
            minutes = 0
        except ValueError:
            raise ValueError("Invalid time format.")
        
    return datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
def _parse_slurm_submit_time(t):
    return datetime.datetime.strptime(t, "%Y-%m-%dT%H:%M:%S")  ## Parse datetime string. Expected format: "2024-01-01T00:00:00"
def _parse_memory_string(m):
    ## Get first number in string before any other characters. Allow for +/- sign and decimal point.
    match = re.search(r'[-+]?\d+(\.\d+)?', m, re.I).group()
    if match:
        return float(match)  ## Return as float
    else:
        return None
def get_jobs_info(username):
    """
    Returns detailed information about each job, including submission time,
    partition, duration, requested resources, and priority.

    Args:
        username (str):
            The username for which to get job information.

    Returns:
        (dict): 
            A dictionary containing the following:\n
                * job_id (list): List of job IDs.\n
                * state (list): List of job states.\n
                * submit_time (list): List of job submission times.\n
                * partition (list): List of partitions.\n
                * time_limit (list): List of job time limits.\n
                * nodes (list): List of nodes.\n
                * cpus (list): List of CPUs.\n
                * memory (list): List of memory.\n
                * priority (list): List of job priorities.
    """
    ## Get job information
    ### squeue -u <username> --Format=(properties.values())
    jobs_info = subprocess.check_output(["squeue", "-u", username, "--Format", ",".join(properties.values())]).decode().strip().split('\n')[1:]
    
    ## Handle case where no jobs are running
    if len(jobs_info) == 0:
        return {key: [] for key in properties}
    
    ji_dict = {key: [re.split(' +', jobs_info[i_line])[i_key] for i_line in range(len(jobs_info))] for i_key, key in enumerate(properties.keys())}
    
    ## Convert time limit and submit time to datetime objects
    ji_dict['time_limit'] = [_parse_slurm_duration(t) for t in ji_dict['time_limit']]
    ji_dict['time_left']  = [_parse_slurm_duration(t) for t in ji_dict['time_left']]
    ji_dict['submit_time'] = [_parse_slurm_submit_time(t) for t in ji_dict['submit_time']]
    
    ## Get numeric values from memory string using regex
    ji_dict['memory'] = [_parse_memory_string(m) for m in ji_dict['memory']]
    
    ## Convert nodes and cpus to integers
    ji_dict['nodes'] = [int(n) for n in ji_dict['nodes']]
    ji_dict['cpus'] = [int(c) for c in ji_dict['cpus']]

    ## Convert priority to floats
    ji_dict['priority'] = [float(p) for p in ji_dict['priority']]
    
    return ji_dict


def manage_jobs(
    username: str = 'rhakim', 
    constraint: str = 'nodes',
    value_max: int = 12, 
    order_jobs_by: str = 'submit_time',
    verbose: int = 0,
    dry_run: bool = False,
) -> None:
    """
    Manages jobs based on the specified constraints.
    RH 2024

    Args:
        username (str):
            The username for which to manage jobs.
        constraint (str):
            The constraint to manage jobs by. Jobs will be held if the sum of
            the constraint on running jobs exceeds the value. For 'fairshare',
            the user's fairshare score will be used as the constraint.\n
            Options:\n
                * 'nodes': Number of nodes.\n
                * 'cpus': Number of CPUs.\n
                * 'memory': Total memory.\n
                * 'time_left': Total time left.\n
                * 'jobs': Total number of running jobs.\n
                * 'fairshare': Fairshare score for user.\n
        value_max (int):
            The maximum value for the constrained resource on running jobs.
        order_jobs_by (str):
            PENDING jobs will be released in order of this constraint.\n
            Options include all keys in the 'properties' dict.
        verbose (int):
            Verbosity level.\n
                * 0: No output.\n
                * 1: Warnings.\n
                * 2: Commands executed.\n
                * 3: Debugging output.\n
        dry_run (bool):
            If True, do not actually hold or release jobs.\n
            Should be used with verbose>1 to see what would be done.
    """
    verbose = int(verbose)  ## Ensure verbosity is an integer

    ## Get jobs information
    jobs = get_jobs_info(username)
    print(f"Fetched jobs. Found {len(jobs['job_id'])} jobs.") if verbose > 1 else None
    print(f"squeue keys found: {jobs.keys()}") if verbose > 2 else None
    ## Assert all values are the same length
    assert all([len(val) == len(jobs['job_id']) for val in jobs.values()]), "Length mismatch in jobs dict."

    ## Append another key to jobs dict for 'job' which is the number of running jobs
    jobs['jobs'] = [1 for _ in jobs['job_id']]

    ## Handle case where no jobs are running
    if len(jobs['job_id']) == 0:
        print("No jobs found. No action taken.") if verbose > 1 else None
        return None
    
    ##  Sort jobs based on the order_by preference
    idx_ordered = native_argsort(jobs[order_jobs_by])[::-1]  ## Descending order of 'order_by'
    jobs_sorted = {key: [val[idx] for idx in idx_ordered] for key, val in jobs.items()}  ## Dict with each list sorted by 'order_by' from highest to lowest
    jobs_sorted_running, jobs_sorted_pending = (
        {
            key: [
                jobs[key][idx] for idx in idx_ordered if jobs['state'][idx] == state
            ] for key in jobs_sorted.keys()
        } for state in ['RUNNING', 'PENDING']
    )  ## Split jobs_sorted into RUNNING and PENDING jobs
    print(f"Jobs sorted by {order_jobs_by}.") if verbose > 2 else None
    
    ## Get constrained resource value
    if constraint == 'fairshare':
        ## Get fairshare for user
        fairshare = float(subprocess.check_output(["sshare", "-u", username, "-U"]).decode().strip().split('\n')[-1].split()[-1])
        value_constrained = fairshare
    else:
        value_constrained = sum(jobs_sorted_running[constraint])
    print(f"Value constrained calculated: {value_constrained}") if verbose > 2 else None
    
    if value_constrained >= value_max:
        print(f"value_constrained ({value_constrained}) >= value_max ({value_max}). Executing scontrol hold on {len(jobs_sorted_pending['job_id'])} jobs.") if verbose > 1 else None
        # Hold any pending jobs
        for i_job, job_id in enumerate(jobs_sorted_pending['job_id']):
            if 'JobHeldUser'.lower() not in jobs_sorted_pending['node_reason'][i_job].lower():
                try:
                    subprocess.run(["scontrol", "hold", job_id]) if not dry_run else None
                except subprocess.CalledProcessError as e:
                    print(f"Error holding job {job_id}.") if verbose > 0 else None
                print(f"Holding job {job_id}.") if verbose > 2 else None
            else:
                print(f"Job {job_id} already held.") if verbose > 2 else None
    else:
        print(f"Value constrained < value_max. Entering release mode.") if verbose > 2 else None
        ## Calculate number of jobs to release
        ### Get cumulative sum of the constraint for each pending job
        cumsum = list(itertools.accumulate(jobs_sorted_pending[constraint]))
        print(f"cumsum of constraint: {cumsum}") if verbose > 2 else None
        ### Get number of jobs to release
        n_jobs_to_release = sum([1 for c in cumsum if c + value_constrained <= value_max])
        print(f"value_constrained ({value_constrained}) < value_max ({value_max}). Executing scontrol release on {n_jobs_to_release} jobs.") if verbose > 1 else None
        ### Release jobs
        for i_job, job_id in enumerate(jobs_sorted_pending['job_id']):
            if i_job < n_jobs_to_release:
                try:
                    subprocess.run(["scontrol", "release", job_id]) if not dry_run else None
                except subprocess.CalledProcessError as e:
                    print(f"Error releasing job {job_id}.") if verbose > 0 else None
                print(f"Releasing job {job_id}.") if verbose > 2 else None
            else:
                print(f"Job {job_id} not released.") if verbose > 2 else None
                break

    return None


#################
#### HELPERS ####
#################

def native_argsort(l):
    """
    Native Python argsort. Returns the indices that would sort a list.
    RH 2024

    Args:
        l (list):
            List to sort

    Returns:
        (list):
            List of indices that would sort the input list.
    """
    return sorted(range(len(l)), key=lambda k: l[k])
                

class _RepeatTimer(threading.Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)



if __name__ == "__main__":
    args = parse_args()
    value_max, constraint, order_by, interval, duration, username, verbose, dry_run, no_daemon = (
        args.value_max, args.constraint, args.order_by, args.interval, args.duration, args.username, args.verbose, args.dry_run, args.no_daemon
    )
    username = subprocess.check_output(["whoami"]).decode().strip() if username is None else username

    if verbose > 0:
        print(f"STARTING JOB HOLDER")
        print(f"Managing jobs for user: {username}, Constraint: {constraint}, Max value: {value_max}, Order by: {order_by}, Interval: {interval} seconds")

    fn_manage_jobs = lambda: manage_jobs(
        username=username, 
        constraint=constraint, 
        value_max=value_max, 
        order_jobs_by=order_by,
        verbose=verbose,
        dry_run=dry_run,
    )

    fn_manage_jobs()
    if not no_daemon:
        timer = _RepeatTimer(interval, fn_manage_jobs)
        timer.start()
        time.sleep(duration)
        timer.cancel()
        print("Exiting job holder.") if verbose > 0 else None