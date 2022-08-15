===================================
Account Abstraction - EIP 4337
===================================

An account abstraction proposal which completely avoids the need for consensus-layer protocol changes. Instead of adding new protocol features and changing the bottom-layer transaction type, this proposal instead introduces a higher-layer pseudo-transaction object called a **UserOperation**.

Users send UserOperation objects into a separate mempool. A special class of actor called bundlers (either miners, or users that can send transactions to miners through a bundle marketplace) package up a set of these objects into a transaction making a ``handleOps()`` call to a special contract, and that transaction then gets included in a block.

This project is an implementation of `EIP-4337 <https://github.com/ethereum/EIPs/blob/master/EIPS/eip-4337.md>`_ Account Abstraction

This project provides:

* The core contracts and interfaces (`on github <https://github.com/eth-infinitism/account-abstraction/tree/main/contracts>`_)

* Javascript client library

* Test suite for the contracts.



Check out the :doc:`usage` section for further information, including
how to :ref:`installation` the project.

.. note::

   The contracts of the project are audited.

   The client library is under active development.

Contents
--------

.. toctree::

   usage
   architecture
   api
