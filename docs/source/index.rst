.. tv-generator documentation master file, created by
   sphinx-quickstart on Tue Jun 17 01:14:49 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to tv-generator's documentation!
========================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules

Usage
-----

.. code-block:: bash

   tvgen build --indir results --outdir specs
   tvgen validate --spec specs/crypto.yaml

.. code-block:: bash

   tvgen scan --symbols BTCUSD,ETHUSD --market crypto --columns close
   tvgen preview --market crypto | head
   tvgen bundle --format yaml --outfile bundle.yaml



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
