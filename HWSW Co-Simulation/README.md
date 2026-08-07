## ABS MPSoC Deployment Co-Simulator (Open Science & Reproducibility Package)

This repository provides a fully parameterizable, calibration-free Python-based **digital twin** that replicates the HW/SW co-simulation results of the Automatic Braking System (ABS) case study presented in our paper:

> **"Toward a context-driven deployment optimization for embedded systems: a product line approach"**  
> *The Journal of Supercomputing (2022)* [2].

### 1. Overview & Physical Grounding
Unlike closed-source or complex SystemC-based environments, this package delivers a highly transparent and reproducible alternative to the SCoPE library [3, 4]. Rather than relying on hardcoded lookup tables, the engine computes system metrics organically across **100 periodic simulation frames** using fundamental physical and real-time scheduling equations [3, 5]:
* **Dynamic CMOS Power:** Core active power is dynamically calculated based on the heterogeneous processor speed, operational voltage (DVFS), and active execution time.
* **Thermal-Static Leakage Loop:** Static leakage power is modeled as an exponential function of junction temperature rise, which is determined by the average active power dissipation and package thermal resistance (\\(R_{thermal} = 15^\circ\text{C/W}\\)) [6].
* **RTOS Context-Switch Penalties:** Every scheduled task is penalized by an OS microkernel context-switch overhead of \\(0.5\text{ Million Instructions (MI)}\\).
* **Shared Bus Contention:** When multiple concurrent inter-core communications occur simultaneously over the system bus, a 15% latency penalty per concurrent contender is dynamically applied.

### 2. Validated Reproducibility (Figs. 11 & 12)
By executing this engine, you will organically reproduce the dual-axis optimization curves of the paper:
1. **The Energy Curve (Fig. 11):** Verifies the characteristic U-shaped curve, identifying the energy minimum at exactly **5 Processing Elements (PEs)** (~3.02 GJ), where parallel task mapping prevents core overloading and minimizes thermal leakage, before rising at 6 PEs due to bus contention and heterogeneous core static footprint [5, 7].
2. **CPU Utilization Boxplots (Fig. 12):** Confirms that only the 5 and 6 PE configurations successfully respect the safety-critical **80% maximum CPU utilization limit** [5, 7].

### 3. Usage & Customization
To ensure maximum flexibility and support Design Space Exploration (DSE) [8], the software specifications and MPSoC hardware architectures are completely decoupled from the execution engine and loaded dynamically from standard CSV files.

To run the simulator and generate the quantitative report along with the publication-quality visualization dashboard, run:
```bash
python3 scope_simulator-v6.py --tasks application_tasks.csv --platform hardware_platform.csv --output scope_simulation_results-v7.png

