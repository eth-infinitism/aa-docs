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
   
Just using the Contracts:
------------------------

.. code-block:: console

   yarn install @account-abstraction/contracts
   
From solidity code:

.. code-block:: javascript

   import "@account-abstraction/contracts/BaseWallet.sol";
   
   contract MyContract is BaseWallet { 
     ...
   }


Just JSON artifacts:

.. code-block:: javsascript

   artifact = require('@account-abstraction/contracts/artifacts/EntryPoint.json')

js/ts code::

.. code-block:: javsascript

   const {EntryPoint__factory} = require("@account-abstraction/contracts/typechain/factories/EntryPoint__factory");
   ...
   const entryPoint = EntryPoint__factory.connect(entryPointAddress, signer)


.
