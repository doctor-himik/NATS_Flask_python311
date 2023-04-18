## How to launch a project?

1. Make sure you've docker and python 3.11 installed on your computer. Run command `python -m pip install --upgrade pip`
2. Make sure there's internet connection to make docker images available to be downloaded
3. We need to pull nats image using. `docker pull nats:latest` `docker run -p 4222:4222 -ti nats:latest` or it will be done by docker-compose
4. Run terminal from the project root and use command: `docker-compose build` and `docker-compose up` or just `docker-compose up`
5. Now we can use CLI running commands like: `main.py -operator add 133 -882` where: 
   *  `-operator` is a base parameter
   * `add` is one of available operation
   * `133` and `-882` are A and B values to apply operation, here accepted only int or float.
   * Also, we can use `-help` to see available operation
    
## How to check that solutions works fine? - Run tests!
1. Run terminal from the project root
2. Run command `python -m pip install --upgrade pip` if you haven't done it earlier
3. Run command `pip install -r requirements.txt` to install project packages
4. Run command `pip install -r test_requirements.txt` to install packages for test porpuses
5. Now we can run tests
6. Run particular test_file like: `python -m pytest ./tests/worker/test_worker.py -v` for e2e tests run entire solution
7. Run all tests in project: `python -m pytest -v` WARNING! - Make sure that solution is running cause
8. Also, we can run unit tests only with: `pytest -m unit` - you can run any time
9. Also, we can run unit tests only with: `pytest -m integration` there are few of them 
10. Also, we can run end-two-end tests only with: `pytest -m e2e` WARNING! - Make sure that solution is running before launching E2E tests. 
11. Finally, you can try Web UI on `http://localhost:5002/index` or just `http://localhost:5002/` work with it


## Helpers and troubleshooting
1. Clean docker completely - `docker system prune -a` in case of problems with containers and strange docker network behavior
2. Clean Vemmem process - open CMD `wsl --shutdown` if OS Windows and RAM leaked heavily (it can happen and there ill be needed reboot and some magic start for docker to be launched properly)
3. If there are *timeout problems on NATS* use `docker-compose down` and clean networks with `docker netrowks rm <network_name>` then rebuild `docker-compose build` and `docker-compose up` or point #1
4. If needed to rebuild and launch a container after changes, run: `docker-compose up -d --no-deps --build <CONTAINER_NAME>` it will be rebuilt and relaunched


## Restrictions and trade-offs
There are some restriction and cons in the solution.
1. logging can ruin all the async in the project, but it's needed for problem-solving purposes, better be Kibana async client, but it's an overkill 
2. I didn't implement discovery and protobuf (will do it later just for fun, outside of this test task)
3. It begs to use some sqlite for storing tasks
4. I didn't use protobuf so there is some bad code on serialisation/deserialization stages
5. A lot of parametrization needed for services PORTS, in docker files and docker compose file and through project
6. Front-end is not cool, completely may be better to use CLI not to see that crap :)
7. Poor configuration, no config.toml or similar