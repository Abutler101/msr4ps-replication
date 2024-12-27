# Replication Package - Links Between Package Popularity, Criticality, and Security in Software Ecosystems
### Alexis Butler, Dan O'Keeffe, Santanu Kumar Dash

## Contents
- **./dataset** → A compressed snapshot of the graph dataset, 
                and tooling to load it into Neo4J.
- **./analysis** → Scripts used for all parts of the analysis 
                of packages in the graph dataset.
- **./relationship_analysis** → raw data and spreadsheet used to find
                correlations between popularity, criticality, and security
- **./scorecard_validation** → Code used to validate the use of OSSF
               Scorecard as a proxy for security. Validation makes
               use of static analysis vuln density as a more direct
               security measure.
- **./storage_interface** → (Internal) Src files for interfacing with the GraphDB 
- **./shared_models** → (Internal) Src files defining various datamodels
- **./api_clients** → (Internal) Src files supporting API interactions


## Requirements
- Docker
- Docker Compose V2
- JQ
- Make
- curl
- Python 3.8
- A Python Virtual Environment manager (conda etc.)

## Setup
The Setup instructions for each of the parts of this repo
### Dataset
- Download the zipped dataset from Zenodo: ...
- Move the zipped dataset into the dataset directory
- cd into the dataset directory
- Run `sudo make load data` - this unpacks the dataset snapshot and loads 
  it into a Neo4J instance running on Docker
- Run `make launch` - brings the Neo4J instance up and makes it accessible on 
  port 7687
### Analysis
- Follow all setup steps for graph database
- Run `git submodule init` followed by `git submodule update` to initialise 
  the git-submodule used for topology analysis
- Generate a GitHub API Auth Token
- Paste GitHub API Auth Token into .env file at root of this repo
- Create a Python3.8 virtual environment
- Install dependencies from requirements.txt
### Scorecard Validation
- Follow all previous setup Sections

## Usage Notes
- Analysis scripts are inter-dependant:
  - `degree_distrib.py` -(enables)-> `tail-estimation`
  - `disc_sampling.py` -(enables)-> `disc_ossf_scoring.py`
  - `popularity_sampling.py` -(enables)-> `popularity_ossf_scoring.py`
- `*_ossf_scoring.py` scripts have run times in the multiple hours due to
  rate limits
- for tail estimation (topology analysis) Run `python3 tail-estimation/Python3/tail-estimation.py --verbose 1 --delimiter comma --diagplots 1 --savedata 1 <ABSOLUTE PATH>/output/.../deg_distrib.csv <ABSOLUTE PATH>/output/.../tail_estim`
- 

## Contact
Please raise any issues or questions using the built-in GitHub Issue 
system, Alexis will address them in due course.

## Paper
```
Raw Bibtex cite to paper - Pending Camera Ready Approval
```