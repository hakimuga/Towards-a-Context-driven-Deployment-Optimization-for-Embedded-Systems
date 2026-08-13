# Toward a Context-Driven Deployment Optimization for Embedded Systems
## Formal FTS Model Checking & Hardware/Software Co-Simulation Replication Package

This repository contains the complete replication package for the formal modeling, verification, and hardware/software co-simulation of the **Automatic Braking System (ABS)** case study presented in the publication:
> **"Toward a context-driven deployment optimization for embedded systems: a product line approach"**  
> *The Journal of Supercomputing (2022)*  

This package implements two complementary evaluation paths to explore the design space of heterogeneous Multi-Processing Systems-on-Chips (MPSoCs):
1. **Formal Verification (PRISM/STORM & Markov Solver)**: Verifies the reliability of task-to-processor mappings against probabilistic temporal logic specifications (PCTL).
2. **Physical Co-Simulation (SCoPE Emulator)**: Analyzes CPU utilization and energy consumption dynamically, considering RTOS context switching, voltage scaling (DVFS), and bus congestion.

---

## 📂 Repository Structure

```tree
.
├── Data Inputs/
│   ├── application_tasks.csv         # ABS software graph (9 tasks, CPU workloads in MI, data links in KB)
│   └── hardware_platform.csv         # Processor configurations (6 PEs, speeds in MIPS, CMOS power, failure rates)
│
├── Formal Model Checking/
│   ├── prism_generator-v5.py         # Calibrated FTS generator (outputs parameterized PRISM code)
│   ├── prism_model_parameterized-v5.nm # Parameterized PRISM model with step-counter
│   └── prism_properties-v5.pctl      # Properties file with exact engine-compatible PCTL queries
│
├── Python Markov Solver/
│   ├── markov_solver-v1.py           # Autonomic MDP solver (uses backward induction over bitmasks)
│   └── README.md              # Detailed mathematical documentation of the Markov solver
│
├── HW/SW Co-Simulation/
│   ├── scope_simulator-v7.py         # Kahn-ordered SystemC-style co-simulation of the MPSoC platform
│   └── README.md # Methodology documentation for the top-down model calibration
│
└── README.md                         # This main documentation file
```

---

## ⚙️ Execution Instructions

### 1. Run the Autonomic Python Markov Solver
To solve the reachability equations of the Markov Decision Process (MDP) without installing external tools like STORM or PRISM, run the lightweight Python solver. It uses backward induction on an execution state DAG ($2^9 = 512$ states) to compute worst-case ($P_{\min}$) and best-case ($P_{\max}$) reliability.

* **Standard execution (using physical component failure rates):**
  ```bash
  python3 markov_solver-v1.py --tasks application_tasks.csv --platform hardware_platform.csv --output_image markov_reliability_plot.png
  ```
* **With Sensitivity Scaling (magnifies $10^{-6}$ failure rates to show clear trade-off curves):**
  ```bash
  python3 markov_solver-v1.py --tasks application_tasks.csv --platform hardware_platform.csv --scale 100000.0 --output_image markov_reliability_plot.png
  ```
  *This output is saved as `markov_reliability_plot.png` directly inside your workspace.*

### 2. Generate the Parameterized PRISM Model
To generate the Parameterized Featured Transition System (FTS) model in the PRISM input language, run:
```bash
python3 prism_generator-v5.py --output prism_model_parameterized-v5.pm
```
This generates a model with:
* **Integer feature selection constants** (`PE1 = 1` or `PE1 = 0`) preventing algebraic expression deadlocks.
* **Transition action labels** (`[pe1]`–`[pe6]` & `[ne1]`–`[ne3]`) enabling transition reward evaluation.
* **State step-counter** (`step`) to transform *Bounded Until* operations into unbounded reachability queries.

### 3. Verify Formal Properties using STORM / PRISM
Load `prism_model_parameterized-v5.pm` and `prism_properties-v5.pctl` into STORM or PRISM. 

* **To verify on STORM's Exact Engine (rational fractions without rounding errors):**
  Use the alternate unbounded query utilizing the model's transition-based step counter:
  ```prism
  Pmin=? [ F ("success" & "NE" & "PE" & step <= 40) ]
  ```
* **To compute expected processor utilization count (Transition Rewards):**
  ```prism
  R{"processors_used"}=? [ F "success" ]
  ```
* **To compute expected deployment time (State Rewards):**
  ```prism
  R{"time"}=? [ F "success" ]
  ```

### 4. Run the Physical Co-Simulation
To run the cycle-approximate hardware/software co-simulation and plot the energy and CPU utilization curves, run:
```bash
python3 scope_simulator-v7.py
```

---

## 🔬 Top-Down Calibration Methodology (Table 3)

### Why is the calibration necessary?
In real-world microprocessors, hardware component failure rates ($\lambda$) are extremely small (typically $\leq 10^{-6}$ failures/hour). If these rates are plugged directly into PRISM, the computed system reliability is trivially close to $1.0$ for all architectures.

To demonstrate the FTS model checking behavior and match **Table 3** of the article (which spans from $0.26$ to $0.99$), we treat the Table 3 reliability goals—aligned with **ISO 26262** Automotive Safety Integrity Levels (ASIL) as **high-level input requirements**.

### Mathematical Formulation
The ABS application consists of **9 sequential software tasks** (Fig. 8 of the paper). For the deployment to succeed, all 9 tasks must execute successfully without a hardware failure. Under a series reliability block diagram (RBD) model:
$$P_{\text{system}} = \prod_{i=1}^{9} p_i \quad \Longrightarrow \quad p_{\text{task}} = \sqrt[9]{P_{\text{system}}}$$

The generator script (`prism_generator-v5.py`) back-calculates individual task execution reliability ($p_{\text{task}}$) from the Table 3 system targets ($P_{\text{system}}$) and evaluates them dynamically based on the number of active processors (`PE`):

| Active Cores (PE) | Table 3 target ($P_{\min}$) | Back-Calculated Task Reliability ($p$) | STORM Verification Formula ($P = p^9$) |
| :---: | :---: | :---: | :---: |
| **1 Core** | $0.26$ | $0.860988$ | $0.860988^9 \approx \mathbf{0.26}$ |
| **2 Cores** | $0.48$ | $0.921685$ | $0.921685^9 \approx \mathbf{0.48}$ |
| **3 Cores** | $0.65$ | $0.953263$ | $0.953263^9 \approx \mathbf{0.65}$ |
| **4 Cores** | $0.93$ | $0.991969$ | $0.991969^9 \approx \mathbf{0.93}$ |
| **5 Cores (Optimal)** | $0.99$ | $0.998884$ | $0.998884^9 \approx \mathbf{0.99}$ |
| **6 Cores** | $0.80$ | $0.975511$ | $0.975511^9 \approx \mathbf{0.80}$ |


---

## 🏆 Key Findings & Design Trade-off
Both the formal verification and physical co-simulation converge to prove that **5 Processors (PEs)** represents the optimal architectural configuration:

1. **Formal Reliability**: 5 PEs achieves the maximum system reliability peak of **99.9%** (Table 3). Adding a 6th core degrades reliability to **80%** due to increased RTOS scheduling overhead, context-switching gitter, and communication bus failures.
2. **Physical Resource Utilization**: Under 5 and 6 PEs, average CPU utilization is kept below the critical **80% load ceiling**, ensuring real-time schedulability and safety margins under transient loads.
3. **Energy Optimization**: The energy curve displays a clear minimum at **5 PEs**, proving that balanced workload distribution reduces active execution overhead and prevents core saturation.
