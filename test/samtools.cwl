#!/usr/bin/env cwl-runner


- id: "#samtools"
  class: GGPCommandTool
  inputs:
    - id: "#samtools-in-project-id"
      type: string
      label: "Project Id"
      description: "google apps project id"
      inputBinding: {}
    - id: "#samtools-in-service-account"
      type: string
      label: "Service Account"
      description: "service account for google cloud compute"
    - id: "#samtools-in-bucket"
      type: string
      label: "Bucket"
      description: "google storage bucket name"
    - id: "#samtools-in-input-file"
      type: string
      label: "Input File"
      description: "BAM file to act as input to samtools"
    - id: "#samtools-in-output-file"
      type: string
      label: "Input File"
      description: "BAM file to act as input to samtools"
  outputs:
    - id: "#samtools-out-filename"
      type: File
      label: "Output File"
      description: "output bai file"
      outputBinding:
          glob:
             engine: cwl:JsonPointer
             script: /job/samtools-in-output-file
  baseCommand: "samtools"
  arguments:
    "index"
  stdout:
    engine: cwl:JsonPointer
    script: /job/samtools-in-output-file


- id: "#main"
  class: Workflow
  label: "Samtools"
  description: "run samtools on google pipeline"
  inputs:
     - id: "#project-id"
       type: string
     - id: "#service-account"
       type: string
     - id: "#bucket"
       type: string
     - id: "#input-file"
       type: string
     - id: "#output-file"
       type: string
  outputs:
    - id: "#main.output"
      type: File
      source: "#samtools.samtools-out-filename"
  steps :
    - id: "#step0"
      run: {import: "#samtools"}
      inputs:
        - { id: "#samtools.samtools-in-project-id" ,  source: "#project-id" }
        - { id: "#samtools.samtools-in-service-account",  source: "#service-account" }
        - { id: "#samtools.samtools-in-bucket",  source: "#bucket" }
        - { id: "#samtools.samtools-in-input-file",  source: "#input-file" }
        - { id: "#samtools.samtools-in-output-file",  source: "#output-file" }
      outputs:
        - { id: "#samtools.samtools-out-filename", default: "default-output.txt" }

