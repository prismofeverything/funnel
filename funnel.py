import string
import json
import sys
from pprint import pprint

import cwltool.draft2tool
import cwltool.workflow
import cwltool.main
import cwltool.process
import cwltool.docker

from oauth2client.client import GoogleCredentials
from apiclient.discovery import build

import logging
logger = logging.getLogger('funnel.pipeline')
logger.setLevel(logging.INFO)

class Pipeline(object):
    def __init__(self):
        self.credentials = GoogleCredentials.get_application_default()
        self.service = build('genomics', 'v1alpha2', credentials=self.credentials)

    def create_input_parameters(self, inputs):
        input_parameters = []
        for input in inputs:
            suffix = inputs[input].split('.')[-1]
            parameter = {
                'name': input,
                'description': input,
                'localCopy': {
                    'path': input + '.' + suffix,
                    'disk': 'data'
                }
            }
            input_parameters.append(parameter)

        return input_parameters

    def input_command(self, input_parameters):
        command = ['/mnt/data/' + parameter['localCopy']['path'] for parameter in input_parameters]
        return string.join(command, ' ')

    def create_pipeline(self, project_id, container, command, inputs):
        input_parameters = self.create_input_parameters(inputs)
        create_body = {
            'projectId': project_id,
            'name': 'Samtools Index',
            'description': 'Run "samtools index" on a BAM file',
            'docker' : {
                'cmd': command + ' ' + self.input_command(input_parameters) + ' /mnt/data/output.bam.bai',
                'imageName': 'gcr.io/' + project_id + '/' + container
            },
            'inputParameters' : input_parameters,
            'outputParameters' : [{
                'name': 'outputFile',
                'description': 'GCS path for where to write the BAM index',
                'localCopy': {
                    'path': 'output.bam.bai',
                    'disk': 'data'
                }
            }],
            'resources' : {
                'disks': [{
                    'name': 'data',
                    'autoDelete': True,
                    'mountPoint': '/mnt/data',
                    'sizeGb': 10,
                    'type': 'PERSISTENT_HDD',
                }],
                'minimumCpuCores': 1,
                'minimumRamGb': 1,
            }
        }

        pipeline = self.service.pipelines().create(body=create_body).execute()
        return pipeline

    def run_pipeline(self, container, project_id, pipeline_id, service_account, bucket, inputs, output_file):
        run_body = {
            'pipelineId': pipeline_id,
            'pipelineArgs' : {
                'inputs': inputs,
                'outputs': {
                    'outputFile': 'gs://' + bucket + '/' + output_file
                },
                'logging': {
                    'gcsPath': 'gs://' + bucket + '/pipelines-api-examples/' + container + '/logging'
                },
                'projectId': project_id,
                'serviceAccount': {
                    'email': service_account,
                    'scopes': [
                        'https://www.googleapis.com/auth/cloud-platform'
                    ]
                }
            }
        }

        pipeline = self.service.pipelines().run(body=run_body).execute()
        return pipeline

    def funnel_to_pipeline(self, project_id, container, command, service_account, bucket, inputs, output_file):
        pipeline = self.create_pipeline(project_id, container, command, inputs)
        pipeline_id = pipeline["pipelineId"]
        pprint(pipeline)

        result = self.run_pipeline(container, project_id, pipeline_id, service_account, bucket, inputs, output_file)
        pprint(result)

        return result

class PipelineParameters(object):
    def __init__(self, filename):
        self.filename = filename

    def parse(self):
        with open(self.filename) as data:
            self.parameters = json.load(data)

        return self.parameters

class PipelineJob(object):
    def __init__(self, spec, pipeline, pipeline_args):
        self.spec = spec
        self.pipeline = pipeline
        self.pipeline_args = pipeline_args
        self.running = False

    def run(self, dry_run=False, pull_image=True, **kwargs):
        id = self.spec['id']
        input_ids = [input['id'].replace(id + '#', '') for input in self.spec['inputs']]
        inputs = {input: self.builder.job[input]['path'] for input in input_ids}

        result = self.pipeline.funnel_to_pipeline(
            self.pipeline_args['project-id'],
            self.pipeline_args['container'],
            string.join(self.spec['baseCommand'], ' '),
            self.pipeline_args['service-account'],
            self.pipeline_args['bucket'],
            inputs,
            self.pipeline_args['output-file']
        )

        self.output_callback({'pipeline-output': result}, 'success')

class PipelinePathMapper(cwltool.pathmapper.PathMapper):
    def __init__(self, referenced_files, basedir):
        self._pathmap = {}
        for src in referenced_files:
            if src.startswith("gs://"):
                ab = src
            else:
                ab = cwltool.pathmapper.abspath(src, basedir)
            self._pathmap[src] = (ab, ab)

class PipelineTool(cwltool.draft2tool.CommandLineTool):
    def __init__(self, spec, pipeline, pipeline_args, **kwargs):
        super(PipelineTool, self).__init__(spec, **kwargs)
        self.spec = spec
        self.pipeline = pipeline
        self.pipeline_args = pipeline_args

    def makeJobRunner(self):
        return PipelineJob(self.spec, self.pipeline, self.pipeline_args)

    def makePathMapper(self, reffiles, input_basedir, **kwargs):
        return PipelinePathMapper(reffiles, input_basedir)

class PipelineRunner(object):
    def __init__(self, pipeline, pipeline_args):
        self.pipeline = pipeline
        self.pipeline_args = pipeline_args

    def output_callback(self, out, status):
        if status == "success":
            logger.info("Job completed!")
        else:
            logger.info("Job failed...")
        self.output = out

    def pipeline_make_tool(self, spec, **kwargs):
        if "class" in spec and spec["class"] == "CommandLineTool":
            return PipelineTool(spec, self.pipeline, self.pipeline_args, **kwargs)
        else:
            return cwltool.workflow.defaultMakeTool(spec, **kwargs)

    def pipeline_executor(self, tool, job_order, input_basedir, args, **kwargs):
        job = tool.job(job_order, input_basedir, self.output_callback, docker_outdir="$(task.outdir)", **kwargs)

        for runnable in job:
            if runnable:
                runnable.run(**kwargs)

        return self.output

def main(args):
    pipeline_args = {
        'project-id': 'machine-generated-837',
        'service-account' : 'SOMENUMBER-compute@developer.gserviceaccount.com',
        'bucket' : 'your-bucket',
        'container' : 'samtools',
        'output-file' : 'path/to/where/you/want/google/pipeline/to/put/your/output'
    }

    parser = cwltool.main.arg_parser()
    pipeline = Pipeline()
    runner = PipelineRunner(pipeline, pipeline_args)
    cwltool.main.main(args, executor=runner.pipeline_executor, makeTool=runner.pipeline_make_tool, parser=parser)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))