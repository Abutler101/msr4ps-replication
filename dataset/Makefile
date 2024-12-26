SHELL := bash
launch:
	# Launch the DozerDB (Neo4J Community edition + plugin to add enterprise edition functionality) container
	docker compose up -d

down:
	# Bring down the DozerDB container but leave the volume (graph data) intact
	docker compose down

load-data: launch down
	# Launch GraphDB to trigger the creation of the directory structure, bring the container down to avoid corruption
	# Decompress and copy the snapshot of the directory structure - replacing the docker volume with the datasets
	unzip dataset-snapshot.zip
	@MOUNTPOINT=$$(docker inspect  msr4ps-dataset_graphdata | jq -r ".[0].Mountpoint") && \
	cp -r msr4ps_graphdata/_data/* $$MOUNTPOINT
	rm -rf msr4ps_graphdata __MACOSX
