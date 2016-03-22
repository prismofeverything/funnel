#!/usr/bin/env cwl-runner

- id: "#samtools"
  class: CommandLineTool
  inputs:
    - id: "#samtools-input-file"
      type: string
      label: "Input File"
      description: "BAM file to act as input to pipeline"
      inputBinding: {}
    - id: "#samtools-output-file"
      type: string
      label: "Output file"
      description: "The file containing the result"
  outputs:
    - id: "#samtools-output"
      type: File
      label: "Output File"
      description: "output bai file"
      outputBinding:
          glob:
             engine: cwl:JsonPointer
             script: /job/samtools-output-file
  baseCommand: ["samtools", "index"]
  stdout:
    engine: cwl:JsonPointer
    script: /job/samtools-output-file

- id: "#main"
  class: Workflow
  label: "Samtools"
  description: "run samtools on a bam file"
  inputs:
     - id: "#input-file"
       type: string
  outputs:
    - id: "#main.output"
      type: File
      source: "#samtools.samtools-output"
  steps :
    - id: "#step0"
      run: {import: "#pipeline"}
      inputs:
        - { id: "#pipeline.pipeline-input-file",  source: "#input-file" }
        - { id: "#pipeline.pipeline-output-file",  source: "#output-file" }
      outputs:
        - { id: "#pipeline.pipeline-output" }

