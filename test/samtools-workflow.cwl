#!/usr/bin/env cwl-runner

class: Workflow

inputs:
  - id: "#input"
    type: File
    description: "bam file"

outputs:
  - id: "#bai"
    type: File
    source: "#samindex.output"

hints:
  - class: DockerRequirement
    dockerLoad: gcr.io/level-elevator-714/samtools
    dockerImageId: sha256:f8de369e9dddf875c5f53c5aada66596d12affccf8b96da15a00c48a1b3a4be9

steps:
  - id: "#samindex"
    run: { import: samtools-index.cwl }
    inputs:
      - { id: "#samindex.input", source: "#input" }
    outputs:
      - { id: "#samindex.output" }

# works with the following command
# --------------------------------
# 
# docker run -i --volume=/Users/spanglry/Code/pipelines-api-examples/samtools/test_mnt/input/NA06986.chromMT.ILLUMINA.bwa.CEU.exon_targetted.20100311.bam:/var/lib/cwl/job52690104_input/NA06986.chromMT.ILLUMINA.bwa.CEU.exon_targetted.20100311.bam:ro --volume=/Users/spanglry/Code/pipelines-api-examples/samtools/test_mnt/output:/var/spool/cwl:rw --volume=/var/folders/2l/0wpdpqws4jvg9lqjwrhvdcl8_c3ksp/T/tmppwPp18:/tmp:rw --workdir=/var/spool/cwl --read-only=true --net=none --user=1000 --rm --env=TMPDIR=/tmp sha256:f8de369e9dddf875c5f53c5aada66596d12affccf8b96da15a00c48a1b3a4be9 samtools index /var/lib/cwl/job52690104_input/NA06986.chromMT.ILLUMINA.bwa.CEU.exon_targetted.20100311.bam indexed.bam.bai