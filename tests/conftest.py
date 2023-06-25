import pytest
import sys
import os

# add the directory containing your project to the sys.path list
project_dir = os.path.abspath('../scarlet')
sys.path.append(project_dir)


def pytest_addoption(parser):
    parser.addoption("--all", action="store_true", help="run all combinations")


def pytest_generate_tests(metafunc):
    if "param1" in metafunc.fixturenames:
        if metafunc.config.getoption("all"):
            end = 5
        else:
            end = 2
        metafunc.parametrize("param1", range(end))