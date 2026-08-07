import os
import math
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg') # Headless rendering
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Set, Tuple

class ParameterizableMarkovSolver:
    """
    A parameterizable Python engine that computes the Markov Decision Process (MDP)
    state-space reliability of the MPSoC deployment directly from CSV inputs.
    Replaces the need for PRISM/STORM model checkers by solving the reachability equations
    using backwards induction / value iteration over the task graph's state space DAG.
    """
    def __init__(self, tasks_csv: str, platform_csv: str):
        self.tasks_csv = tasks_csv
        self.platform_csv = platform_csv
        self.load_configuration()
        
        # Default network bus configurations (Section 5.1)
        self.buses = {
            'NE1': {'rate': 1000.0, 'lambda_b': 1e-7},
            'NE2': {'rate': 2000.0, 'lambda_b': 1.2e-7},
            'NE3': {'rate': 1500.0, 'lambda_b': 1.5e-7}
        }
        
        # Communication links (data sizes in KB)
        self.links = {
            ('BrakePedal', 'EmergencyStop'): 15.0,
            ('EmergencyStop', 'LoadCompensator'): 25.0,
            ('WSR_F', 'LoadCompensator'): 20.0,
            ('WSR_R', 'LoadCompensator'): 20.0,
            ('LoadCompensator', 'ABS_Main'): 40.0,
            ('CruiseControl', 'ABS_Main'): 30.0,
            ('ABS_Main', 'WAC_F'): 35.0,
            ('ABS_Main', 'WAC_R'): 35.0
        }

    def load_configuration(self):
        print(f"Loading software tasks from: {self.tasks_csv}")
        df_tasks = pd.read_csv(self.tasks_csv)
        self.tasks = {}
        for _, row in df_tasks.iterrows():
            name = row['task_name']
            wl = float(row['workload_mi'])
            preds_raw = row['predecessors']
            preds = [p.strip() for p in preds_raw.split(';')] if pd.notna(preds_raw) and str(preds_raw).strip() != "" else []
            self.tasks[name] = {'wl': wl, 'preds': preds}

        self.task_names = list(self.tasks.keys())
        self.task_to_idx = {name: i for i, name in enumerate(self.task_names)}

        print(f"Loading hardware platform from: {self.platform_csv}")
        df_plat = pd.read_csv(self.platform_csv)
        self.pe_profiles = {}
        for _, row in df_plat.iterrows():
            pe_id = int(row['pe_id'])
            self.pe_profiles[pe_id] = {
                'name': f"PE{pe_id}",
                'speed': float(row['speed_mips']),
                'lambda_p': float(row['failure_rate'])
            }

    def get_reliability_pe(self, task: str, pe_id: int, scale_factor: float = 1.0) -> float:
        wl = self.tasks[task]['wl']
        speed = self.pe_profiles[pe_id]['speed']
        lambda_p = self.pe_profiles[pe_id]['lambda_p'] * scale_factor
        return math.exp(-(wl / speed) * lambda_p)

    def get_reliability_bus(self, src: str, tgt: str, bus: str, scale_factor: float = 1.0) -> float:
        size = self.links.get((src, tgt), 20.0)
        rate = self.buses[bus]['rate']
        lambda_b = self.buses[bus]['lambda_b'] * scale_factor
        return math.exp(-(size / rate) * lambda_b)

    def solve_mdp(self, n_pes: int, active_buses: List[str], scale_factor: float = 1.0) -> Tuple[float, float]:
        """
        Solves the MDP using backward induction over the DAG state space.
        """
        active_pe_ids = list(range(1, n_pes + 1))
        num_tasks = len(self.task_names)
        num_states = 1 << num_tasks
        
        v_min = np.zeros(num_states)
        v_max = np.zeros(num_states)
        
        # Base case
        success_state = num_states - 1
        v_min[success_state] = 1.0
        v_max[success_state] = 1.0

        for state in range(num_states - 2, -1, -1):
            ready_tasks = []
            for t_idx, t_name in enumerate(self.task_names):
                if not (state & (1 << t_idx)):
                    preds_done = True
                    for pred in self.tasks[t_name]['preds']:
                        pred_idx = self.task_to_idx[pred]
                        if not (state & (1 << pred_idx)):
                            preds_done = False
                            break
                    if preds_done:
                        ready_tasks.append((t_idx, t_name))
            
            if not ready_tasks:
                v_min[state] = 0.0
                v_max[state] = 0.0
                continue

            p_choices_min = []
            p_choices_max = []

            for t_idx, t_name in ready_tasks:
                next_state = state | (1 << t_idx)
                
                for pe_id in active_pe_ids:
                    r_pe = self.get_reliability_pe(t_name, pe_id, scale_factor)
                    
                    r_comm = 1.0
                    for pred in self.tasks[t_name]['preds']:
                        bus_reliabilities = [self.get_reliability_bus(pred, t_name, bus, scale_factor) for bus in active_buses]
                        if bus_reliabilities:
                            r_comm *= min(bus_reliabilities)

                    p_step = r_pe * r_comm
                    
                    val_min = p_step * v_min[next_state]
                    val_max = p_step * v_max[next_state]
                    
                    p_choices_min.append(val_min)
                    p_choices_max.append(val_max)

            v_min[state] = min(p_choices_min) if p_choices_min else 0.0
            v_max[state] = max(p_choices_max) if p_choices_max else 0.0

        return v_min[0], v_max[0]

    def plot_reliability_curves(self, results: List[dict], output_image_path: str):
        """
        Plots worst-case and best-case reliability curves over core configurations.
        """
        sns.set_theme(style='whitegrid', palette='colorblind', font='DejaVu Sans')
        
        pes = [r['n_pes'] for r in results]
        p_mins = [r['p_min'] for r in results]
        p_maxs = [r['p_max'] for r in results]
        
        fig, ax = plt.subplots(figsize=(8, 5.5))
        
        ax.plot(pes, p_maxs, marker='o', color='#2ca02c', linewidth=2.5, markersize=8, label='Best-Case Reliability (P_max)')
        ax.plot(pes, p_mins, marker='s', color='#d62728', linewidth=2.0, markersize=8, linestyle='--', label='Worst-Case Reliability (P_min)')
        
        ax.set_title('Direct MDP Markovian Solver: Reliability over MPSoC Core Count', fontsize=12, fontweight='bold', pad=12)
        ax.set_xlabel('Processing Elements (PEs)', fontsize=10, labelpad=8)
        ax.set_ylabel('Probability of Successful Deployment', fontsize=10, labelpad=8)
        ax.set_xticks(pes)
        ax.set_ylim(min(p_mins) - 0.02, 1.02)
        ax.legend(loc='lower right')
        
        sns.despine()
        plt.tight_layout()
        fig.savefig(output_image_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"Reliability curves plot saved to: {output_image_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Markovian Solver in Python.")
    parser.add_argument("--tasks", default="application_tasks.csv", help="Path to software tasks CSV")
    parser.add_argument("--platform", default="hardware_platform.csv", help="Path to hardware platform CSV")
    parser.add_argument("--scale", type=float, default=1.0, help="Failure rate scale factor for illustration")
    parser.add_argument("--output_image", default="markov_reliability_plot.png", help="Path to save output chart")
    args = parser.parse_args()

    # Re-route to find CSVs if stored elsewhere
    tasks_path = "application_tasks.csv" if not os.path.exists(args.tasks) else args.tasks
    plat_path = "hardware_platform.csv" if not os.path.exists(args.platform) else args.platform

    solver = ParameterizableMarkovSolver(tasks_path, plat_path)
    
    results = []
    print("\n==========================================================================================")
    print("                     DIRECT PYTHON MARKOVIAN DEPENDABILITY REPORT                          ")
    print("==========================================================================================")
    print(f"{'PEs':<6} | {'Worst-Case Reliability (P_min)':<32} | {'Best-Case Reliability (P_max)':<32}")
    print("-" * 90)
    for n in range(1, 7):
        p_min, p_max = solver.solve_mdp(n, ['NE1', 'NE2', 'NE3'], args.scale)
        print(f"{n:<6} | {p_min:<32.12f} | {p_max:<32.12f}")
        results.append({'n_pes': n, 'p_min': p_min, 'p_max': p_max})
    print("==========================================================================================\n")
    
    # Generate visualization
    solver.plot_reliability_curves(results, args.output_image)
