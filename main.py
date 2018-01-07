import os
import logging
import logging.config
import json
import sys
import argparse
import timeit

from topicSHARK.topicshark import topicSHARK
from mongoengine import connect
from pycoshark.mongomodels import Project
from pycoshark.utils import create_mongodb_uri_string
from pycoshark.utils import get_base_argparser


def setup_logging(default_path=os.path.dirname(os.path.realpath(__file__))+"/loggerConfiguration.json",
                  default_level=logging.INFO):
        """
        Setup logging configuration

        :param default_path: path to the logger configuration
        :param default_level: defines the default logging level if configuration file is not found(default:logging.INFO)
        """
        path = default_path
        if os.path.exists(path):
            with open(path, 'rt') as f:
                config = json.load(f)
            logging.config.dictConfig(config)
        else:
            logging.basicConfig(level=default_level)


def start():
    start = timeit.default_timer()
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("Starting topicSHARK...")

    parser = get_base_argparser('Create a topic model.', '1.0.0')
    parser.add_argument('-n', '--project-name', help='Name of the project to analyze.', required=True)
    parser.add_argument('--topic_name', help='Name of the topic model in the database.')
    parser.add_argument('--plugin_path', help='Path of the plugin', required='true')
    parser.add_argument('-k', '--K', help='How many topics are expected', default=6)

    parser.add_argument('--filter_language', help='Filter for Programming Language')
    parser.add_argument('--filter_project', help='Filter for specific Project')
    
    parser.add_argument('--issue', help='Use Issues for Topic Model', default='true')
    parser.add_argument('--issue_comments', help='Use Issue Comments for Topic Model', default='true')
    parser.add_argument('--messages', help='Use Messages for Topic Model', default='false')
    parser.add_argument('--passes', help='Steps for building the Topic Model', default=20)
    parser.add_argument('--output', help='Output Folder', required='true')

    parser.add_argument('--debug', help='Sets the debug level.', default='DEBUG',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])

    args = parser.parse_args()
    uri = create_mongodb_uri_string(args.db_user, args.db_password, args.db_hostname, args.db_port, args.db_authentication, args.ssl)

    connect(args.db_database, host=uri)
    logger.info("Project:" + args.project_name)

    project = Project.objects.get(name=args.project_name)
    config = {'product_name': args.project_name,
              'topic_name' : args.topic_name,
              'K' : int(args.K),
              'filter' : args.plugin_path + "/wordfilter.txt",
              'language_filter' : args.filter_language,
              'project_filter' :  args.filter_project,
              'issue_comments' :  args.issue_comments,
              'issues' : args.issue,
              'messages' : args.messages,
	      'output' : args.output,
              'passes' : int(args.passes),
              'project_id': project.id}   

    c = topicSHARK()
    c.configure(config)
    c.start()

    c.uploadToGridFS()
    
    end = timeit.default_timer() - start
    logger.info("Finished topicSHARK in {:.5f}s".format(end))

if __name__ == "__main__":
    start()
