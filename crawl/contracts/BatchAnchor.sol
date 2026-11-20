// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Stores Merkle roots for off-chain legal-answer receipts.
contract BatchAnchor {
    address public immutable owner;

    struct Batch {
        uint64 count;
        uint64 anchoredAt;
    }

    mapping(bytes32 => Batch) public batches;

    event BatchAnchored(bytes32 indexed root, uint64 count, uint64 anchoredAt, address indexed submitter);

    error NotOwner();
    error InvalidBatch();
    error AlreadyAnchored();

    constructor() {
        owner = msg.sender;
    }

    function anchor(bytes32 root, uint64 count) external {
        if (msg.sender != owner) revert NotOwner();
        if (root == bytes32(0) || count == 0) revert InvalidBatch();
        if (batches[root].anchoredAt != 0) revert AlreadyAnchored();
        uint64 timestamp = uint64(block.timestamp);
        batches[root] = Batch(count, timestamp);
        emit BatchAnchored(root, count, timestamp, msg.sender);
    }
}
