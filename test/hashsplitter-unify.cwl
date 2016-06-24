#!/usr/bin/env cwl-runner

cwlVersion: "draft-3"

class: CommandLineTool

description: "unify hashed values into a single output"

inputs:
  
  - id: md5
    type: File
    inputBinding:
      position: 1

  - id: sha
    type: File
    inputBinding:
      position: 2

  - id: whirlpool
    type: File
    inputBinding:
      position: 3

outputs:
  - id: output
    type: File
    outputBinding:
      glob: unify

stdout: unify

baseCommand: [cat]

