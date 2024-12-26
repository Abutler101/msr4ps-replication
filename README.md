# Replication Package - Links Between Package Popularity, Criticality, and Security in Software Ecosystems
### Alexis Butler, Dan O'Keeffe, Santanu Kumar Dash

### Contents
- **./dataset** → A compressed snapshot of the graph dataset, 
                and tooling to load it into Neo4J.
- **./analysis** → Scripts used for all parts of the analysis 
                of packages in the graph dataset.
- **./scorecard_validation** → Code used to validate the use of OSSF
               Scorecard as a proxy for security. Validation makes
               use of static analysis vuln density as a more direct
               security measure.


### Requirements
- Docker
- Docker Compose V2
- JQ
- Make
- curl
- Python 3.8
- A Python Virtual Environment manager (conda etc.)

### Setup
The Setup instructions for each of the parts of this repo
#### Dataset
- Download the zipped dataset from Zenodo: https://zenodo.org/records/14561974
- Move the zipped dataset into the dataset directory
- cd into the dataset directory
- Run `sudo make load data` - this unpacks the dataset snapshot and loads 
  it into a Neo4J instance running on Docker
- Run `make launch` - brings the Neo4J instance up and makes it accessible on 
  port 7687
#### Analysis
- Placeholder
#### Scorecard Validation
- Placeholder

### Usage
- Placeholder

### Contact
Please raise any issues or questions using the built-in GitHub Issue 
system, Alexis will address them in due course.

### Paper
```
Raw Bibtex cite to paper
```