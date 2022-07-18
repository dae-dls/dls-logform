PYTHONPATH = src
PACKAGE_DIR = dls_logform

# ------------------------------------------------------------------
# Tests.
test-01-simple:
	PYTHONPATH=$(PYTHONPATH) python3 -m pytest -sv --basetemp=/tmp/$(PACKAGE_DIR) tests/test_logform.py::Test_01::test_01
	
test-02-exception:
	PYTHONPATH=$(PYTHONPATH) python3 -m pytest -sv --basetemp=/tmp/$(PACKAGE_DIR) tests/test_logform.py::Test_02::test_02
	
test-03-stack:  # Run stack test in pytest.
	PYTHONPATH=$(PYTHONPATH) python3 -m pytest -sv --basetemp=/tmp/$(PACKAGE_DIR) tests/test_logform.py::Test_03::test_03
	
# ------------------------------------------------------------------
# GitLab CI.

gitlab_ci_test: 
	python3 -m pytest -sv -ra --basetemp=/tmp/$(PACKAGE_DIR) --cov=$(PACKAGE_DIR) tests

test-ci:
	PYTHONPATH=$(PYTHONPATH) make gitlab_ci_test

pytest:
	PYTHONPATH=$(PYTHONPATH) pytest

# ------------------------------------------------------------------
# Utility.

build_docs:
	PYTHONPATH=$(PYTHONPATH) \
	sphinx-build -EWT --keep-going docs build/html
	touch build/html/.nojekyll

#  331  wget https://github.com/GitCredentialManager/git-credential-manager/releases/download/v2.0.785/gcm-linux_amd64.2.0.785.tar.gz
#  334  tar -xvf gcm-linux_amd64.2.0.785.tar.gz -C /usr/local/bin
#  335  git-credential-manager-core configure
#  338  yum install -y libicu libsecret
#  339  git-credential-manager-core configure
#  341  export GCM_CREDENTIAL_STORE=secretservice
#  342  git subtree push --prefix build/html origin gh-pages
#  345  export GCM_CREDENTIAL_STORE=gpg
#  346  git subtree push --prefix build/html origin gh-pages
 
publish_docs:
	

.PHONY: list
list:
	@awk "/^[^\t:]+[:]/" Makefile | grep -v ".PHONY"

tree:
	tree -I "__*" $(PACKAGE_DIR)

show-version:
	PYTHONPATH=$(PYTHONPATH) python3 -m dls_logform.version --json
	PYTHONPATH=$(PYTHONPATH) python3 -m dls_logform.version

# ------------------------------------------------------------------
# Version bumping.  Configured in setup.cfg. 
# Thanks: https://pypi.org/project/bump2version/
bump-patch:
	bump2version --list patch

bump-minor:
	bump2version --list minor

bump-major:
	bump2version --list major
	
bump-dryrun:
	bump2version --dry-run patch
	