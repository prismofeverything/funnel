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

  def create_parameters(self, puts, replace=False):
    parameters = []
    for put in puts:
      path = puts[put]
      if replace:
        path = path.replace("gs://", '')

      parameter = {
        'name': put,
        'description': put,
        'localCopy': {
          'path': path,
          'disk': 'data'
        }
      }
      parameters.append(parameter)

    return parameters

  def input_command(self, input_parameters):
    command = ['/mnt/data/' + parameter['localCopy']['path'] for parameter in input_parameters]
    return string.join(command, ' ')

  def create_pipeline(self, project_id, container, service_account, bucket, command, inputs, outputs, output_path, mount):
    input_parameters = self.create_parameters(inputs, True)
    output_parameters = self.create_parameters(outputs)
    
    create_body = {
      'ephemeralPipeline': {
        'projectId': project_id,
        'name': 'funnel workflow',
        'description': 'run a google pipeline from cwl',
        
        'docker' : {
          'cmd': command,
          'imageName': 'gcr.io/' + project_id + '/' + container
        },
        
        'inputParameters' : input_parameters,
        'outputParameters' : output_parameters,
        
        'resources' : {
          'disks': [{
            'name': 'data',
            'autoDelete': True,
            'mountPoint': mount,
            'sizeGb': 10,
            'type': 'PERSISTENT_HDD',
          }],
          'minimumCpuCores': 1,
          'minimumRamGb': 1,
        }
      },
        
      'pipelineArgs' : {
        'inputs': inputs,
        'outputs': {output: 'gs://' + bucket + '/' + output_path + '/' + outputs[output] for output in outputs},
        
        'logging': {
          'gcsPath': 'gs://' + bucket + '/' + project_id + '/' + container + '/logging'
        },
        
        'projectId': project_id,
        
        'serviceAccount': {
          'email': service_account,
          'scopes': ['https://www.googleapis.com/auth/cloud-platform']
        }
      }
    }
    
    return create_body
    
  def run_pipeline(self, body):
    return self.service.pipelines().run(body=body).execute()
    
  def funnel_to_pipeline(self, project_id, container, service_account, bucket, command, inputs, outputs, output_path, mount):
    body = self.create_pipeline(project_id, container, service_account, bucket, command, inputs, outputs, output_path, mount)
    pprint(body)
    
    result = self.run_pipeline(body)
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
    
    pprint(self.spec)

    input_ids = [input['id'].replace(id + '#', '') for input in self.spec['inputs']]
    inputs = {input: self.builder.job[input]['path'] for input in input_ids}
    
    output_path = self.pipeline_args['output-path']
    outputs = {output['id'].replace(id + '#', ''): output['outputBinding']['glob'] for output in self.spec['outputs']}

    command_parts = self.spec['baseCommand'][:]
    command_parts.extend(self.spec['arguments'])
    command = string.join(command_parts, ' ')
    
    mount = '/mnt/data'
    if self.spec['stdout']:
      command += ' > ' + mount + '/' + self.spec['stdout']

    result = self.pipeline.funnel_to_pipeline(
      self.pipeline_args['project-id'],
      self.pipeline_args['container'],
      self.pipeline_args['service-account'],
      self.pipeline_args['bucket'],
      command,
      inputs,
      outputs,
      output_path,
      mount
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
        logger.info("Running! " + str(runnable))
        runnable.run(**kwargs)
        
    return self.output

def main(args):
  pipeline_args = {
    # 'project-id': 'machine-generated-837',
    # 'service-account' : 'SOMENUMBER-compute@developer.gserviceaccount.com',
    # 'bucket' : 'your-bucket',
    # 'container' : 'samtools',
    # 'output-file' : 'path/to/where/you/want/google/pipeline/to/put/your/output'
  }
  
  parser = cwltool.main.arg_parser()
  pipeline = Pipeline()
  runner = PipelineRunner(pipeline, pipeline_args)
  cwltool.main.main(args, executor=runner.pipeline_executor, makeTool=runner.pipeline_make_tool, parser=parser)

if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))

