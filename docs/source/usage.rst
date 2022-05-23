Usage
=====

.. _installation:

Installation
------------

To install locally, do:

.. code-block:: console

   git clone https://github.com/eth-infinitism/account-abstraction.git
   cd account-abstraction
   yarn install
   yarn test
   
To run a sample operation against the goerli miner do

.. code-block:: console

   export MNEMONIC_FILE=<account-on-goerli>
   yarn runop-goerli

