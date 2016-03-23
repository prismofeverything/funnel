# funnel

Trigger the Google Genomics Pipeline API with CWL

## Goal and Disclaimer

The goal of this project is to accept a CWL file that would be used to fire a command line tool provided as a Docker container and instead trigger that container on the Google Genomics Pipeline API (GP).

Currently this project is incomplete. You can hand it a CWL file specifying a local input and output, but GP only accepts inputs from a Google Bucket (GB) and only outputs to a GB. The next step would be to take the input file provided to CWL and upload it to a GB, run the GP, then download the output from the output GB and provide it as the output for CWL.

Beyond that, since GP really only performs single jobs of a single Docker container, this project does not yet support chaining. Ideally, you could take a CWL specifying an arbitrary directed acyclic graph workflow of tools to run and it would run them on GP instead. In this case, the output of one tool could be kept in a GB and provided to the next stage of the workflow, only downloading the final output once complete. Or leaving it up there, as the case may be.

As it is, this performs a single operation of a single container.

## Usage

In order to run this, you must have a [GP enabled account](https://cloud.google.com/genomics/install-genomics-tools) and have gathered enough information to fill out this input dict (located in the `main` function of `funnel.py`):

```python
    pipeline_args = {
        'project-id': 'machine-generated-837',
        'service-account' : 'SOMENUMBER-compute@developer.gserviceaccount.com',
        'bucket' : 'your-bucket',
        'container' : 'docker-container',
        'command' : 'command line',
        'input-file' : 'gs://path/to/an/input/file/in/some/bucket/somewhere',
        'output-file' : 'path/to/where/you/want/google/pipeline/to/put/your/output'
    }
```

Once you've done that, you can test this with the following command:

```
python funnel.py test/samtools-workflow.cwl --input test/samtools-workflow.cwl
```

(Notice the dumb usage of the cwl as the input file also: this is because currently the input is a pointer to a file in a GB specified inside the python script and ignores this argument entirely).

This will output the results from the GP, including the informative line:

```
u'name': u'operations/EP7WnIa6KhiimNLAnK-r3aYBIPGRzLvVHCoPcHJvZHVjdGlvblF1ZXVl'
```

Take this operations id and put it [into the box here](https://developers.google.com/apis-explorer/#p/genomics/v1alpha2/genomics.operations.get) to see how it goes.

Enjoy!