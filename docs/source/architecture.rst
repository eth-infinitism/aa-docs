Architecture
============

Multiple attemps have been made by Vitalik & Ethereum's community to incorporate AA into the the system with :eth1.x:`eth1.x <>` and :eip-2938:`eip-2938 <>`. But all of them required significant protocol changes at a time when protocol developers were focusing heavily on the merge and scalability. This is where :eip-4337:`EIP-4337 <>` comes in with the same benifits without consensus-layer protocol changes.

Components
----------

To understand it's complete architecture let's first define the components that are involved

* :ref:`UserOperation <UserOperation>`

* :ref:`Client library <Client library>`

* :ref:`Bundler <Bundler>`

* :ref:`EntryPoint contract <EntryPoint contract>`

* :ref:`Wallet contract <Wallet contract>`

* :ref:`Paymaster contract <Paymaster contract>`


How does this proposal work?
------------------------------

Instead of modifying the logic of the consensus layer itself, we replicate the functionality of the transaction mempool in a higher-level system. Users send ``UserOperation`` objects that package up the user’s intent along with signatures and other data for verification to public mempool dedicated for ``UserOperations``. Bundlers package up a set of ``UserOperation`` objects into a single **bundle transaction**, which then gets included into an Ethereum block.


.. image:: images/mempool-flow.png

.. _UserOperation:

UserOperation
-------------

Users send ``UserOperation`` objects to a dedicated user operation mempool. A specialized class of actors called :ref:`bundlers <Bundler>` listen in on the user operation mempool, and create **bundle transactions**. A bundle transaction packages up multiple ``UserOperation`` objects into a single ``handleOps`` call to a pre-published singleton global **entry point contract**. UserOperation structure is defined as following:


.. list-table:: UserOperation model
   :widths: 25 25 50
   :header-rows: 1

   * - Field
     - Type
     - Description

   * - ``sender``
     - ``address``
     - The wallet making the operation

   * - ``nonce``
     - ``uint256``
     - Anti-replay parameter; also used as the salt for first-time wallet creation

   * - ``initCode``
     - ``bytes``
     - The initCode of the wallet (only needed if the wallet is not yet on-chain and needs to be created)

   * - ``callData``
     - ``bytes``
     - The data to pass to the `sender` during the main execution call

   * - ``callGas``
     - ``uint256``
     - The amount of gas to allocate the main execution call

   * - ``verificationGas``
     - ``uint256``
     - The amount of gas to allocate for the verification step

   * - ``preVerificationGas``
     - ``uint256``
     - The amount of gas to pay for to compensate the bundler for pre-verification execution and calldata

   * - ``maxFeePerGas``
     - ``uint256``
     - Maximum fee per gas (similar to EIP 1559 `max_fee_per_gas`)

   * - ``maxPriorityFeePerGas``
     - ``uint256``
     - Maximum priority fee per gas (similar to EIP 1559 `max_priority_fee_per_gas`)

   * - ``paymaster``
     - ``address``
     - Address sponsoring the transaction (or zero for regular self-sponsored transactions)

   * - ``paymasterData``
     - ``bytes``
     - Extra data to send to the paymaster

   * - ``signature``
     - ``bytes``
     - Data passed into the wallet along with the nonce during the verification step

.. _Client library:

Client library
--------------

Clients accept the ``UserOperation`` from users & verifies it before they can be added to a mempool for it to be processeed by a :ref:`bundler <Bundler>`. Every client must first run some basic sanity checks before they include a ``UserOperation`` into the mempool, namely that:

* Either the ``sender`` is an existing contract, or the ``initCode`` is not empty (but not both)
* The ``verificationGas`` is sufficiently low ``(<= MAX_VERIFICATION_GAS)`` and the ``preVerificationGas`` is sufficiently high (enough to pay for the calldata gas cost of serializing the ``UserOperation`` plus ``PRE_VERIFICATION_OVERHEAD_GAS``)
* The paymaster is either the zero address or is a contract which (i) currently has nonempty code on chain, (ii) has registered and staked, (iii) has a sufficient deposit to pay for the UserOperation, and (iv) is not currently banned.
* The callgas is at least the cost of a ``CALL`` with non-zero value.
* The ``maxFeePerGas`` and ``maxPriorityFeePerGas`` are above a configurable minimum value that the client is willing to accept. At the minimum, they are sufficiently high to be included with the current ``block.basefee``.
* The sender doesn't have another ``UserOperation`` already present in the pool (or it replaces an existing entry with the same sender and nonce, with a higher ``maxPriorityFeePerGas`` and an equally increased ``maxFeePerGas``). Only one ``UserOperation`` per sender may be included in a single batch

If the ``UserOperation`` object passes these sanity checks, the client must next run the first op :ref:`simulation <Simulation>`, and if the simulation succeeds, the client must add the ``UserOperation`` to the mempool.

.. _Bundler:

Bundlers
--------

Bundlers are either miners running special-purpose code, or users that can relay transactions to miners. Bundlers scan the mempool and select ``UserOperation`` objects that benifit them the most, i.e, sort them based on the gas they will receive at the end of inclusion into the block. Before accepting a ``UserOperation``, bundlers must use an RPC method to locally :ref:`simulate <Simulation>` calling the ``simulateValidation`` function of the entry point, to verify that the signature is correct and the operation actually pays fees. Once they filter the ``UserOperation`` objects that they want to include, they bundle them together and either execute it themselves or forward it to a miner.

.. _EntryPoint contract:

EntryPoint contract
------------------------------

Entry point contract is a singleton global contract which has following interface::

    function handleOps
        (UserOperation[] calldata ops, address payable beneficiary)
        public;

    function simulateValidation
        (UserOperation calldata userOp)
        external returns (uint256 preOpGas, uint256 prefund);

For every ``UserOperation``, the entry point's ``handleOps`` function must make two loops (the verification loop and the execution loop). There can be two cases for every ``UserOperation``, either it has ``paymaster`` information  (contract that is ready to sponsor gas) or it doesn't.

No Paymaster case
*****************

Let's first describe the simpler no paymaster case. In the verification loop, the ``handleOps`` call must perform the following steps for each ``UserOperation``:

* **Create the wallet if it does not yet exist**, using the initcode provided in the ``UserOperation``. If the wallet does not exist, and the initcode is empty, or the newly deployed contract address differs from ``UserOperation.sender``, the call must fail.
* **Call ``validateUserOp`` on the wallet**, passing in the ``UserOperation`` and the required fee. The wallet should verify the operation's signature, and pay the fee if the wallet considers the operation valid. If any ``validateUserOp`` call fails, ``handleOps`` must skip execution of at least that operation, and may revert entirely.

In the execution loop, the ``handleOps`` call must perform the following steps for each ``UserOperation``:

* **Call the wallet with the UserOperation's calldata**. It's up to the wallet to choose how to parse the calldata; an expected workflow is for the wallet to have an execute function that parses the remaining calldata as a series of one or more calls that the wallet should make.
* **Refund unused gas fees** to the wallet

.. image:: images/no-paymaster-flow.png

Paymaster case
*****************

We extend the entry point logic to support **paymasters** that can sponsor transactions for other users. This feature can be used to allow application developers to subsidize fees for their users, allow users to pay fees with ERC-20 tokens and many other use cases. When the paymaster is not equal to the zero address, the entry point implements a different flow:

.. image:: images/paymaster-flow.png

During the verification loop, in addition to calling ``validateUserOp``, the ``handleOps`` execution also must check that the paymaster is staked, and also has enough ETH deposited with the entry point to pay for the operation, and then call ``validatePaymasterUserOp`` on the paymaster to verify that the paymaster is willing to pay for the operation. Additionally, the ``validateUserOp`` must be called with a ``requiredPrefund`` of 0 to reflect that it's the paymaster, and not the wallet, that's paying the fees.

During the execution loop, the ``handleOps`` execution must call ``postOp`` on the paymaster after making the main execution call. It must guarantee the execution of ``postOp``, by making the main execution inside an inner call context, and if the inner call context reverts attempting to call ``postOp`` again in an outer call context.

Maliciously crafted paymasters can DoS the system. To prevent this, we use a paymaster reputation system; see the :ref:`reputation, throttling and banning <Reputation, Throttling and Banning>` section for details.


.. _Wallet Contract:

Wallet Contract
---------------

The core interface required for a wallet to have is::

    function validateUserOp
        (UserOperation calldata userOp, bytes32 requestId, uint256 missingWalletFunds)
        external;



.. _Paymaster Contract:

Paymaster Contract
------------------

The paymaster interface is as follows::

    function validatePaymasterUserOp
        (UserOperation calldata userOp, bytes32 requestId, uint256 maxCost)
        external view returns (bytes memory context);

    function postOp
        (PostOpMode mode, bytes calldata context, uint256 actualGasCost)
        external;

    enum PostOpMode {
        opSucceeded, // user op succeeded
        opReverted, // user op reverted. still has to pay for gas.
        postOpReverted // user op succeeded, but caused postOp to revert
    }

To prevent attacks involving malicious ``UserOperation`` objects listing other users' wallets as their paymasters, the entry point contract must require a paymaster to call the entry point to lock their stake and thereby consent to being a paymaster. Unlocking stake must have a delay. The extended interface for the entry point, adding functions for paymasters to add and withdraw stake, is::

    // add a paymaster stake (must be called by the paymaster)
    function addStake(uint32 _unstakeDelaySec) external payable

    // unlock the stake (must wait unstakeDelay before can withdraw)
    function unlockStake() external

    // withdraw the unlocked stake
    function withdrawStake(address payable withdrawAddress) external

The paymaster must also have a deposit, which the entry point will charge ``UserOperation`` costs from. The entry point must implement the following interface to allow paymasters (and optionally wallets) manage their deposit::

    // return the deposit of an account
    function balanceOf(address account) public view returns (uint256)

    // add to the deposit of the given account
    function depositTo(address account) public payable

    // withdraw from the deposit
    function withdrawTo(address payable withdrawAddress, uint256 withdrawAmount) external

.. _Simulation:

Simulation
----------

To simulate a ``UserOperation`` ``op`` validation, the client makes an ``eth_call`` with the following params::

    {
        "from": 0x0000000000000000000000000000000000000000,
        "to": [entry point address],
        "input": [simulateValidation header] + serialize(op),
    }

If the call returns an error, the client rejects the ``op``.

The simulated call performs the full validation, calling both ``wallet.validateUserOp`` and (if specified) ``paymaster.validatePaymasterUserOp``. The two operations differ in their opcode banning policy. In order to distinguish between the two, there is a single call to the NUMBER opcode ``(block.number)``, used as a delimiter between wallet validation restrictions and paymaster validation restrictions. While simulating ``op`` validation, the client should make sure that:

1 Neither call's execution trace invokes any **forbidden opcodes**
2 The first call does not access mutable state of any contract except the wallet itself and its deposit in the entry point contract. Mutable state definition includes both storage and balance.
3 The second call does not access mutable state of any contract except the paymaster itself.
4 Any ``CALL`` or ``CALLCODE`` during validation has value=0, except for the transfer from the wallet to the entry point.
5 No ``CALL``, ``DELEGATECALL``, ``CALLCODE``, ``STATICCALL`` results in an out-of-gas revert.
6 Any ``GAS`` opcode is followed immediately by one of { ``CALL``, ``DELEGATECALL``, ``CALLCODE``, ``STATICCALL`` }.
7 ``EXTCODEHASH`` of every address accessed (by any opcode) does not change between first and second simulations of the op.
8 If ``op.initcode.length != 0`` , allow only one CREATE2 opcode call, otherwise forbid ``CREATE2``.

Since the wallet is allowed to access its own entry point deposit in order to top it up when needed, the client must know the storage slot in order to whitelist it. The entry point therefore implements the following view function::

    function getSenderStorage(address sender) external view returns (uint256[] memory senderStorageCells)

During batching, the client should:

* Exclude UserOps that access any sender address created by another UserOp on the same batch (via CREATE2 factory).
* For each paymaster used in the batch, keep track of the balance while adding UserOps. Ensure that it has sufficient deposit to pay for all the UserOps that use it.

After creating the batch, before including the transaction in a block, the client should:

* Run ``eth_estimateGas`` with maximum possible gas, to verify the entire ``handleOps`` batch transaction, and use the estimated gas for the actual transaction execution.
* If the call reverted, check the ``FailedOp`` event. A ``FailedOp`` during ``handleOps`` simulation is an unexpected event since it was supposed to be caught by the single-UserOperation simulation. Remove the failed op that caused the revert from the batch and drop from the mempool. Other ops from the same paymaster should be removed from the current batch, but kept in the mempool. Repeat until ``eth_estimateGas`` succeeds.

In practice, restrictions (2) and (3) basically mean that the only external accesses that the wallet and the paymaster can make are reading code of other contracts if their code is guaranteed to be immutable (eg. this is useful for calling or delegatecalling to libraries).

If any of the three conditions is violated, the client should reject the op. If both calls succeed (or, if ``op.paymaster == ZERO_ADDRESS`` and the first call succeeds) without violating the three conditions, the client should accept the op. On a bundler node, the storage keys accessed by both calls must be saved as the ``accessList`` of the ``UserOperation``

When a bundler includes a bundle in a block it must ensure that earlier transactions in the block don't make any UserOperation fail. It should either use access lists to prevent conflicts, or place the bundle as the first transaction in the block.

Forbidden opcodes
*****************

The forbidden opcodes are to be forbidden when ``depth > 2`` (i.e. when it is the wallet, paymaster, or other contracts called by them that are being executed). They are: ``GASPRICE``, ``GASLIMIT``, ``DIFFICULTY``, ``TIMESTAMP``, ``BASEFEE``, ``BLOCKHASH``, ``NUMBER``, ``SELFBALANCE``, ``BALANCE``, ``ORIGIN``, ``GAS``, ``CREATE``, ``COINBASE``. They should only be forbidden during verification, not execution. These opcodes are forbidden because their outputs may differ between simulation and execution, so simulation of calls using these opcodes does not reliably tell what would happen if these calls are later done on-chain.

Exceptions to the forbidden opcodes:

1. A single ``CREATE2`` is allowed if ``op.initcode.length != 0`` and must result in the deployment of a previously-undeployed ``UserOperation.sender``.
2. ``GAS`` is allowed if followed immediately by one of { ``CALL``, ``DELEGATECALL``, ``CALLCODE``, ``STATICCALL`` }.


.. _Reputation, Throttling and Banning:

Reputation, Throttling and Banning
----------------------------------

Clients maintain two mappings with a value for each paymaster:

* ``opsSeen: Map[Address, int]``
* ``opsIncluded: Map[Address, int]``

When the client learns of a new ``paymaster``, it sets ``opsSeen[paymaster] = 0`` and ``opsIncluded[paymaster] = 0``.

The client sets ``opsSeen[paymaster] +=1`` each time it adds an op with that ``paymaster`` to the ``UserOperationPool``, and the client sets ``opsIncluded[paymaster] += 1`` each time an op that was in the ``UserOperationPool`` is included on-chain.

Every hour, the client sets ``opsSeen[paymaster] -= opsSeen[paymaster] // 24`` and ``opsIncluded[paymaster] -= opsIncluded[paymaster] // 24`` for all paymasters (so both values are 24-hour exponential moving averages).

We define the **status** of a paymaster as follows::

    OK, THROTTLED, BANNED = 0, 1, 2

    def status(paymaster: Address,
            opsSeen: Map[Address, int],
            opsIncluded: Map[Address, int]):
        if paymaster not in opsSeen:
            return OK
        min_expected_included = opsSeen[paymaster] // MIN_INCLUSION_RATE_DENOMINATOR
        if min_expected_included <= opsIncluded[paymaster] + THROTTLING_SLACK:
            return OK
        elif min_expected_included <= opsIncluded[paymaster] + BAN_SLACK:
            return THROTTLED
        else:
            return BANNED

Stated in simpler terms, we expect at least ``1 / MIN_INCLUSION_RATE_DENOMINATOR`` of all ops seen on the network to get included. If a paymaster falls too far behind this minimum, the paymaster gets **throttled** (meaning, the client does not accept ops from that paymaster if there is already an op from that paymaster, and an op only stays in the pool for 10 blocks), If the paymaster falls even further behind, it gets **banned**. Throttling and banning naturally reverse over time because of the exponential-moving-average rule.

**Non-bundling clients and bundlers should use different settings for the above params:**

.. list-table:: Settings
   :widths: 25 25 50
   :header-rows: 1

   * - Param
     - Client setting
     - Bundler setting

   * - ``MIN_INCLUSION_RATE_DENOMINATOR``
     - 100
     - 10

   * - ``THROTTLING_SLACK``
     - 10
     - 10

   * - ``BAN_SLACK``
     - 50
     - 50

To help make sense of these params, note that a malicious paymaster can at most cause the network (only the p2p network, not the blockchain) to process ``BAN_SLACK * MIN_INCLUSION_RATE_DENOMINATOR / 24`` non-paying ops per hour.

