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
   
To run a sample flow, calling locally the ``EntryPoint.handleOps()``
(note that for non-local network, you need to set ``MNEMONIC_FILE`` environment var to an account that has some eth)

.. code-block:: console

   yarn run runop [ --network hardhat|goerli ]

To run a sample operation against the goerli miner do

.. code-block:: console

   yarn run runop-goerli

