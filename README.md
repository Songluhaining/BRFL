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
We evaluate the performance of BRFL and the baselines using eight software product lines. You can download a complete data versions of  other datasets at [here](https://tuanngokien.github.io/splc2021/).

After preparing the data, set the system_name and buggy_systems_folder parameters in ObtainSusFeatureInteractions.py to execute the script directly. You can run it using the command line, for example:

```sh
python main.py --system "BankAccountTP" --buggy_systems_folder "./examples/4wise-BankAccountTP-1BUG-Full"
```
