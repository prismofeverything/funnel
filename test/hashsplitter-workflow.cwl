#!/usr/bin/env cwlrunner

class: Workflow

cwlVersion: "draft-3"

inputs:

  - id: input
    type: File
    description: "to be hashed all the ways"

outputs:

  - id: output
    type: File
    source: "#unify/output"

steps:

  - id: md5
    run: hashsplitter-md5.cwl
    inputs:
      - { id: input, source: "#input" }
    outputs:
      - { id: output }

  - id: sha
    run: hashsplitter-sha.cwl
    inputs:
      - { id: input, source: "#input" }
    outputs:
      - { id: output }

  - id: whirlpool
    run: hashsplitter-whirlpool.cwl
    inputs:
      - { id: input, source: "#input" }
    outputs:
      - { id: output }

  - id: unify
    run: hashsplitter-unify.cwl
    inputs:
      - { id: md5, source: "#md5/output" }
      - { id: sha, source: "#sha/output" }
      - { id: whirlpool, source: "#whirlpool/output" }
    outputs:
      - { id: output }
