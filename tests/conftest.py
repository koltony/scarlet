import pytest
import sys
import os
import tempfile
import shutil

# add the directory containing your project to the sys.path list
sys.path.append(os.path.abspath('src'))

@pytest.fixture
def test_resource_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)
    

