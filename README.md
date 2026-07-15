# BRFL

## Heterogeneous-Prior Bayesian Inference for Fault Localization in Software Product Lines

### Overview
In our work, we reformulate SPL fault localization as a structured probabilistic causal inference problem. 
The proposed approach models features, statements, and execution outcomes within a factor graph that captures structural and dynamic dependencies across product configurations. 
Instead of relying solely on statistical correlations, we derive heterogeneous prior probabilities from feature--outcome associations and statement-level spectra, incorporating them into Bayesian inference to guide posterior estimation. 
This integration mitigates variability-induced confounding and enables fault probabilities to be inferred without the need for additional test executions.

![](./Framework.png)

### How to Run BRFL

## Requirements

```sh
pip install -r requirements.txt
```
## Subject Systems

We evaluate the performance of BRFL and the baselines on eight software product lines. Among these, we constructed mutants for two larger-scale systems, TankWar and BerkeleyDB, which you can download [here](https://drive.google.com/drive/folders/1NJsldDsFs0yj2GNQYEZSJvgA7Tr7P77u?usp=drive_link). You can also download complete data versions of the other datasets [here](https://tuanngokien.github.io/splc2021/).

> **Note:** Using Javassist requires recompiling the mutants. After setting the mutant directory in `recompile_failed_products.py`, you can recompile them, as shown below.

```sh
python recompile_failed_products.py
```

After preparing the data, set the system_name and buggy_systems_folder parameters in `main.py` to execute the script directly. You can run it using the command line, for example:

```sh
python main.py --system "BankAccountTP" --buggy_systems_folder "./examples/4wise-BankAccountTP-1BUG-Full"
```
