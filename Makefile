PYTHONPATH = .
PACKAGE_DIR = logging_formatter

# ------------------------------------------------------------------
# Tests.
test-01-simple:
	PYTHONPATH=$(PYTHONPATH) python3 -m pytest -sv --basetemp=/tmp/$(PACKAGE_DIR) tests/test_logging_formatter.py::Test_01::test_01
	
test-02-exception:
	PYTHONPATH=$(PYTHONPATH) python3 -m pytest -sv --basetemp=/tmp/$(PACKAGE_DIR) tests/test_logging_formatter.py::Test_02::test_02
	
test-03-stack:  # Run stack test in pytest.
	PYTHONPATH=$(PYTHONPATH) python3 -m pytest -sv --basetemp=/tmp/$(PACKAGE_DIR) tests/test_logging_formatter.py::Test_03::test_03
	
# ------------------------------------------------------------------
# GitLab CI.

gitlab_ci_test: 
	python3 -m pytest -sv -ra --basetemp=/tmp/$(PACKAGE_DIR) --cov=$(PACKAGE_DIR) tests

test-ci:
	PYTHONPATH=$(PYTHONPATH) make gitlab_ci_test

pytest:
	PYTHONPATH=$(PYTHONPATH) pytest

# ------------------------------------------------------------------
# Update code copies.
	
copy-code-testing:
	cp -f logging_formatter/logging_formatter.py $(repo)/tests/logging_formatter.py
	cp -f tests/test_logging_formatter.py $(repo)/tests/test_logging_formatter.py
	@sed -i "s/logging_formatter.logging_formatter/.logging_formatter/g" $(repo)/tests/test_logging_formatter.py

copy-code-library:
	cp -f logging_formatter/logging_formatter.py $(repo)/$(package)/logging_formatter.py
	cp -f tests/test_logging_formatter.py $(repo)/tests/test_logging_formatter.py
	@sed -i "s/logging_formatter.logging_formatter/$(package).logging_formatter/g" $(repo)/tests/test_logging_formatter.py
	
copy-code-lib-maxiv-daqcluster-client:
	@make copy-code-testing repo=../lib-maxiv-daqcluster-client package=daqcluster_client
	
copy-code-dev-maxiv-eiger2:
	@make copy-code-library repo=../dev-maxiv-eiger2 package=dev_maxiv_eiger2
	
copy-code:
	@make copy-code-lib-maxiv-daqcluster-client
	@make copy-code-dev-maxiv-eiger2
	
# ------------------------------------------------------------------
# Conda.

setup:
	PYTHON=python3 bash -x -e ./build.sh

CONDA_BUILD_DIRECTORY = /tmp/conda_build/$(PACKAGE_DIR)
conda-build:
	conda config --set anaconda_upload no
	conda build recipe

CONDA_BUILD_DIRECTORY = /tmp/conda_build/$(PACKAGE_DIR)
conda-build-tmp:
	rm -rf $(CONDA_BUILD_DIRECTORY)
	mkdir -p $(CONDA_BUILD_DIRECTORY)
	conda config --set anaconda_upload no
	conda build --output-folder $(CONDA_BUILD_DIRECTORY) recipe
	tree -I "__*" $(CONDA_BUILD_DIRECTORY)

ANACONDA_TOKEN = 60f3ab1170958f40c75d7509
conda-publish:
	anaconda upload -t $(ANACONDA_TOKEN) $(CONDA_BUILD_DIRECTORY)/noarch/*.tar.bz2

# ------------------------------------------------------------------
# Utility.

.PHONY: list
list:
	@awk "/^[^\t:]+[:]/" Makefile | grep -v ".PHONY"

tree:
	tree -I "__*" $(PACKAGE_DIR)

show-version:
	PYTHONPATH=$(PYTHONPATH) python3 logging_formatter/logging_formatter.py --json
	PYTHONPATH=$(PYTHONPATH) python3 logging_formatter/logging_formatter.py
