#!/usr/bin/env cwl-runner

class: CommandLineTool

description: "Invoke 'samtools index' to create a 'BAI' index (samtools 1.19)"

requirements:
  - class: CreateFileRequirement
    fileDef:
      - filename: indexed.bam
        fileContent:
          engine: "cwl:JsonPointer"
          script: "job/input"

inputs:
  - id: "#input"
    type: File
    description:
      Input bam file.

outputs:
  - id: "#output"
    type: File
    outputBinding:
      glob: "indexed.bam.bai"

baseCommand: ["samtools", "index"]

arguments:
  - "indexed.bam"

