
****************
Installation
****************


From PyPI
#########

TLDR - do this at your own risk
-------------------------------

.. code:: bash

    pip install tyled

Recommended - pipX
------------------

If you don't already have it installed go to https://pypi.org/project/pipx/ for instructions

.. code:: bash

    pipx install tyled

From GitHub
###########

Clone the repository

.. code:: bash

        git clone https://github.com/kfields/tyled.git
        
Navigate to the new directory which contains the repository

.. code:: bash

        cd tyled

Tyled needs Python 3.12 or newer. Create a virtual environment called `.venv`

.. code:: bash

        python3 -m venv .venv

Activate the environment

.. code:: bash

        source .venv/bin/activate

Install tyled, editable, with what the tests need

.. code:: bash

        pip install -e ".[test]"

Run the tests

.. code:: bash

        python -m pytest
