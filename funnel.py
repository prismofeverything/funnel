import sys
import time
import json
import string
import threading

import cwltool.main
import cwltool.docker
import cwltool.process
import cwltool.workflow
import cwltool.draft2tool

# import multiprocessing
# from multiprocessing import Process
from pprint import pprint
from oauth2client.client import GoogleCredentials
from apiclient.discovery import build

# import logging
# logger = logging.getLogger('funnel.pipeline')
# logger.setLevel(logging.INFO)

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

class PipelinePoll(threading.Thread):
  def __init__(self, service, operation, outputs, callback, poll_interval=5):
    super(PipelinePoll, self).__init__()
    self.service = service
    self.operation = operation
    self.poll_interval = poll_interval
    self.outputs = outputs
    self.callback = callback
    self.success = None

  def run(self):
    operation = self.operation
    while not operation['done']:
      time.sleep(self.poll_interval)
      operation = self.service.operations().get(name=operation['name']).execute()

    pprint(operation)
    self.success = operation
    self.callback(self.outputs)

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

    operation = self.pipeline.funnel_to_pipeline(
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
    
    # success = self.pipeline.poll(operation)
    # pprint(success)

    collected = {output: {'path': outputs[output], 'class': 'File', 'hostfs': False} for output in outputs}
    pprint(collected)

    poll = PipelinePoll(self.pipeline.service, operation, collected, lambda outputs: self.output_callback(outputs, 'success'))
    poll.start()
    
    # success = poll.success
    # pprint(success)

    # self.output_callback(collected, 'success')


class PipelinePathMapper(cwltool.pathmapper.PathMapper):
  def __init__(self, referenced_files, basedir):
    self._pathmap = {}
    for src in referenced_files:
      if src.startswith('gs://'):
        ab = src
        iiib = src.split('/')[-1]
        self._pathmap[iiib] = (iiib, ab)
      else:
        ab = cwltool.pathmapper.abspath(src, basedir)

      self._pathmap[ab] = (ab, ab)

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
    # self.lock = threading.Lock()
    # self.cond = threading.Condition(self.lock)
    # self.pool = multiprocessing.Pool(processes=8)

  def output_callback(self, out, status):
    if status == "success":
      print("Job completed!")
    else:
      print("Job failed...")
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


    # jobs = map(lambda j: lambda(r, k): r.run(k), filter(lambda x: x, job))
    # self.pool.map(lambda j: j.run(**kwargs), job)
    # self.pool.join()


    # processes = []
    # for runnable in job:
    #   if runnable:
    #     def run(runnable, kwargs):
    #       print("Running! " + str(runnable))
    #       runnable.run(**kwargs)
    #       print("done running " + str(runnable))

    #     process = Process(target=run, args=[runnable, kwargs])
    #     process.start()
    #     processes.append(process)

    # for process in processes:
    #   process.join()


    # try:
    #     self.cond.acquire()

    #     for runnable in job:
    #         if runnable:
    #             runnable.run(**kwargs)
    #         else:
    #             if self.jobs:
    #                 self.cond.wait(1)
    #             else:
    #                 print('DEADLOCK')
    #                 break

    #     while self.jobs:
    #         self.cond.wait(1)

    # except:
    #     print(sys.exc_info())
    # finally:
    #     self.cond.release()


    # def run(runnable, kwargs):
    #   print("Running! " + str(runnable))
    #   runnable.run(**kwargs)
    #   print("done running " + str(runnable))

    # print(job)
    # print(dir(job))

    # threads = []
    # for runnable in job:
    #   if runnable:
    #     thread = threading.Thread(target=run, args=[runnable, kwargs])
    #     thread.start()
    #     threads.append(thread)

    # for thread in threads:
    #   thread.start()

    # for thread in threads:
    #   thread.join()
        
    print("all processes have joined")
    print(self.output)

    return self.output

def main(args):
  pipeline_args = {
    'project-id': 'level-elevator-714',
    'service-account' : '985014667505-compute@developer.gserviceaccount.com',
    'bucket' : 'hashsplitter',
    'container' : 'hashsplitter',
    'output-path' : 'output'
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

