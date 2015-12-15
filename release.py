#!/usr/bin/env python
# coding: utf-8
import os
import sys
import json
import shutil
import time
import subprocess
from optparse import OptionParser
from django.template.base import Template, Context
from django.conf import settings


settings.configure()


def compile_templates(target_template_dir, destination_template_dir, config):
    """
    Run through template directory and for each template create compiled version
    in destination folder using config as context for Django template rendering.
    """
    template_files = os.listdir(target_template_dir)
    for template in template_files:
        template_path = os.path.join(target_template_dir, template)
        with open(template_path) as f:
            content = f.read()

        tmpl = Template(content)
        context = Context(config)
        content = tmpl.render(context)

        destination_template_path = os.path.join(destination_template_dir, template)
        with open(destination_template_path, 'w') as f:
            f.write(content)


class Release(object):
    """
    Wrapper over rpm-build to build rpm using predefined templates and custom project settings.
    """

    builder_dir_name = os.path.dirname(__file__)
    template_dir_name = 'templates'
    compiled_template_dir_name = 'compiled_templates'
    defaults_file_name = 'defaults.json'
    settings_file_name = 'BUILD.json'

    required_config_keys = [
        "name", "version", "summary", "requires", "build_requires"
    ]

    def __init__(self, project_root=None, defaults_file_path=None, settings_file_path=None):

        # project directory
        self.project_root = project_root or self.get_project_root_path()

        # path to file with default builder settings/parameters
        self.defaults_file_path = defaults_file_path or self.get_defaults_file_path()

        # path to file with project specific builder settings/parameters
        self.settings_file_path = settings_file_path or self.get_settings_file_path()

        # directory with templates to work with
        self.template_root = self.get_template_root_path()

        # directory with templates compiled with final project parameters
        self.compiled_template_root = self.get_compiled_template_root_path()

        # flag to prevent compiling templates twice in one release instance session
        self._compiled = False

    @classmethod
    def get_project_root_path(cls):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def get_template_root_path(self):
        return os.path.join(self.builder_dir_name, self.template_dir_name)

    def get_compiled_template_root_path(self):
        return os.path.join(
            self.builder_dir_name, self.compiled_template_dir_name
        )

    def get_defaults_file_path(self):
        return os.path.join(self.builder_dir_name, self.defaults_file_name)

    def get_settings_file_path(self):
        return os.path.join(self.project_root, self.settings_file_name)

    @staticmethod
    def out(data):
        if not data:
            return
        sys.stdout.write(data)
        if data[-1] != "\n":
            sys.stdout.write("\n")
        sys.stdout.flush()

    @staticmethod
    def load_json_from_file(file_path):
        return json.load(open(file_path, 'r'))

    @staticmethod
    def dump_json_into_file(file_path, data):
        return json.dump(data, open(file_path, 'w'), indent=4)

    def get_defaults_dict(self):
        return self.load_json_from_file(self.defaults_file_path)

    def get_settings_dict(self):
        return self.load_json_from_file(self.settings_file_path)

    def set_settings_dict(self, data):
        return self.dump_json_into_file(self.settings_file_path, data)

    def check_config(self, config):
        missing_keys = set(self.required_config_keys) - set(config.keys())
        if missing_keys:
            raise Exception(
                "missing parameters in {0} file: {1}".format(
                    self.settings_file_name, ", ".join(missing_keys)
                )
            )

    def load_config(self):
        config = {}
        config.update(self.get_defaults_dict())
        config.update(self.get_settings_dict())
        config["project_root"] = self.project_root
        config["release"] = str(int(time.time()))
        config["package_name"] = config.get("package_name", config["name"])
        return config

    def get_config(self):
        config = self.load_config()
        self.check_config(config)
        return config

    def create_compiled_template_root(self):
        if os.path.exists(self.compiled_template_root):
            shutil.rmtree(self.compiled_template_root)
        os.mkdir(self.compiled_template_root)

    @staticmethod
    def get_next_version(current_version):
        major, minor, patch = [int(x) for x in current_version.split('.')]
        patch += 1
        if patch > 99:
            patch = 1
            minor += 1

        return ".".join([str(x) for x in [major, minor, patch]])

    def compile(self):
        """
        Compile templates - create new directory with templates with actual
        values instead of placeholders
        """
        self._compile()

    def _compile(self):
        if self._compiled:
            return
        config = self.get_config()
        self.create_compiled_template_root()
        compile_templates(self.template_root, self.compiled_template_root, config)
        self._compiled = True

    def build(self):
        """
        Create RPM for project
        """
        self._build()

    def _build(self):

        self.compile()

        # run building rpm based on compiled spec via process call to rpmbuild
        spec_file_path = os.path.join(self.compiled_template_root, 'generic_django.spec')
        cmd = ['rpmbuild', '-bb', spec_file_path]
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        for line in iter(process.stdout.readline, b''):
            self.out(line.rstrip())

        self.out(process.stderr.read())

        process.communicate()
        if process.returncode != 0:
            raise Exception('FAILURE, errors occurred when building RPM, see above')

    def deploy(self):
        """
        Automatically increment project version, finalize CHANGELOG, create tag for new release,
        and push all into remote origin repository.
        """
        return self._deploy()

    def _deploy(self):
        build_config = self.get_settings_dict()
        current_version = build_config['version']
        self.out('current version {0}'.format(current_version))
        new_version = self.get_next_version(current_version)
        self.out('new version will be {0}'.format(new_version))

        build_config['version'] = new_version
        self.set_settings_dict(build_config)

        cmd = [
            os.path.join(self.builder_dir_name, 'deploy.sh'),
            self.project_root,
            new_version
        ]
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out, err = process.communicate()
        self.out(out)
        self.out(err)
        if process.returncode != 0:
            build_config['version'] = current_version
            self.set_settings_dict(build_config)
            raise Exception('FAILURE, errors occurred when deploying new version, see above')

        self.out('SUCCESS')

    def get_info(self):
        self.out('use -h flag to view help information\n')


if __name__ == "__main__":

    parser = OptionParser()

    parser.add_option(
        "-c", "--compile",
        action="store_true", dest="compile", default=False,
        help="compile templates"
    )
    parser.add_option(
        "-b", "--build",
        action="store_true", dest="build", default=False,
        help="build rpm"
    )
    parser.add_option(
        "-d", "--deploy",
        action="store_true", dest="deploy", default=False,
        help="create new project version to build"
    )
    (options, args) = parser.parse_args()

    release = Release()

    if options.compile:
        release.compile()

    if options.deploy:
        release.deploy()

    if options.build:
        release.build()

    if not any([options.deploy, options.build, options.compile]):
        release.get_info()
