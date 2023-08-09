# Path Computation Element

[![pce-ci-badge]][pce-ci] [![pce-cov-badge]][pce-cov]

Path Computation Element, also called PCE, is a component of
[Atlanticwave SDX][aw-sdx] project.

The problem PCE aims to solve is this: given a network topology and a
set of connection requests between some nodes in the topology that
must satisfy some requirements (regarding bandwidth, latency, number
of hops, packet loss, etc.) how do we find the right path between the
given nodes?

## Using PCE

PCE's API is still evolving.  With that caveat, and omitting some
details, the general usage is like this:

```python
from sdx_pce.load_balancing.te_solver import TESolver
from sdx_pce.topology.temanager import TEManager

temanager = TEManager(initial_topology, connection_request)
for topology in topologies:
    temanager.add_topology(topology)
    
graph = temanager.generate_graph_te()
traffic_matrix = temanager.generate_connection_te()

solution = TESolver(graph, traffic_matrix).solve()
```

Note that PCE requires two inputs: network topology and connection
requests.  For testing, a random topology generator and a random
connection request generator is available.

In the intermediate steps, network topology is generated by [NetworkX]
and the traffic matrix computation is executed by Google [OR-Tools]
Solver.


### Network Topology

The Network Topology should be in the format of NetworkX graph. For
each link, three attributes need to be assigned: cost, bandwidth and
latency. The current unit of each attribute is abstract, but the unit
in the Network Topology should be consistent with the unit in
Connections.


### Connection Requests

Connection requests should carry an identifier, source, destination,
required bandwidth, and required latency, among other things.  They
are in JSON format.  For an example, see [test_request.json].


## Working with PCE code

Working with PCE in a virtual environment is a good idea, with a
workflow like this:

```console
$ git clone https://github.com/atlanticwave-sdx/pce.git
$ cd pce
$ python3 -m venv venv --upgrade-deps
$ source venv/bin/activate
$ pip install .[test]
```

Please note that editable installs do not work currently, due to the
shared top-level `sdx` module in datamodel.

PCE can read topology data from Graphviz dot files, if the optional
pygraphviz dependency is installed with:

```console
$ pip install .[pygraphviz]
```

In order to be able to install pygraphviz, you will also need a C
compiler and development libraries and headers of graphviz installed.


### Running tests

Use [pytest] to run all tests:

```
$ pip install --editable .[test]
$ pytest
```

If you want to print console and logging messages when running a test,
do:

```
$ pytest --log-cli-level=all [-s|--capture=no] \
    tests/test_te_manager.py::TEManagerTests::test_generate_solver_input
```

Use [tox] to run tests using several versions of Python in isolated
virtual environments:

```
$ tox
```

With tox, you can run a single test verbosely like so:

```
$ tox -e py311 -- --log-cli-level=all [-s|--capture=no] \
    tests/test_te_manager.py::TEManagerTests::test_generate_solver_input
```

The test that depend on pygraphviz are skipped by default.  If you are
able to install pygraphviz in your setup, you can run that test too
with:

```
$ tox -e extras
```

Test data is stored in [tests/data](./tests/data) as JSON files.


<!-- URLs -->

[aw-sdx]: https://www.atlanticwave-sdx.net/ (Atlanticwave-SDX)

[pce-ci-badge]: https://github.com/atlanticwave-sdx/pce/actions/workflows/test.yml/badge.svg
[pce-ci]: https://github.com/atlanticwave-sdx/pce/actions/workflows/test.yml

[pce-cov-badge]: https://coveralls.io/repos/github/atlanticwave-sdx/pce/badge.svg?branch=main (Coverage Status)
[pce-cov]: https://coveralls.io/github/atlanticwave-sdx/pce?branch=main

[NetworkX]: https://networkx.org/
[OR-Tools]: https://developers.google.com/optimization/

[pytest]: https://docs.pytest.org/
[tox]: https://tox.wiki/en/latest/index.html

[test_request.json]: ./src/sdx/pce/data/requests/test_request.json
