#!/usr/bin/env cwl-runner

- id: "#pipeline"
  class: CommandLineTool
  inputs:
    - id: "#pipeline-project-id"
      type: string
      label: "Project Id"
      description: "google apps project id"
      inputBinding: {}
    - id: "#pipeline-service-account"
      type: string
      label: "Service Account"
      description: "service account for google cloud compute"
    - id: "#pipeline-bucket"
      type: string
      label: "Bucket"
      description: "google storage bucket name"
    - id: "#pipeline-container"
      type: string
      label: "Bucket"
      description: "docker container"
    - id: "#pipeline-command"
      type: string
      label: "Bucket"
      description: "command"
    - id: "#pipeline-input-file"
      type: string
      label: "Input File"
      description: "BAM file to act as input to pipeline"
    - id: "#pipeline-output-file"
      type: string
      label: "Input File"
      description: "BAM file to act as input to pipeline"
  baseCommand: "ls"
  outputs:
    - id: "#pipeline-output"
      type: string
      label: "Output File"
      description: "output bai file"
      outputBinding:
          glob:
             engine: cwl:JsonPointer
             script: /job/pipeline-output-file

- id: "#main"
  class: Workflow
  label: "Google Pipeline"
  description: "run a docker container on google pipeline"
  inputs:
     - id: "#project-id"
       type: string
     - id: "#service-account"
       type: string
     - id: "#bucket"
       type: string
     - id: "#container"
       type: string
     - id: "#command"
       type: string
     - id: "#input-file"
       type: string
     - id: "#output-file"
       type: string
  outputs:
    - id: "#main.output"
      type: string
      source: "#pipeline.pipeline-output"
  steps :
    - id: "#step0"
      run: {import: "#pipeline"}
      inputs:
        - { id: "#pipeline.pipeline-project-id",  source: "#project-id" }
        - { id: "#pipeline.pipeline-service-account",  source: "#service-account" }
        - { id: "#pipeline.pipeline-bucket",  source: "#bucket" }
        - { id: "#pipeline.pipeline-container",  source: "#container" }
        - { id: "#pipeline.pipeline-command",  source: "#command" }
        - { id: "#pipeline.pipeline-input-file",  source: "#input-file" }
        - { id: "#pipeline.pipeline-output-file",  source: "#output-file" }
      outputs:
        - { id: "#pipeline.pipeline-output" }

