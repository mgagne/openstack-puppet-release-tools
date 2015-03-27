#!/usr/bin/env python

import argparse
import yaml

from launchpadlib.launchpad import Launchpad


parser = argparse.ArgumentParser(description='Synchronize projects on LP')
parser.add_argument('--config',
                    help='YAML file with projects definitions',
                    default='projects.yaml')
args = parser.parse_args()

with open(args.config, 'r') as f:
    (projects) = yaml.load(f)

lp = Launchpad.login_with('openstack-puppet-modules', 'production')


series_defaults = projects['series']
for project_name, project in list(projects['projects'].items()):
    lp_project = lp.projects[project_name]
    print 'Project: %s' % lp_project.name

    # Compute series from defaults
    project_all_series = project['series']
    for series_name, projet_series in list(project_all_series.items()):
        projet_series = projet_series or dict()
        projet_series.update(series_defaults.get(series_name, {}))
        project_all_series[series_name] = projet_series

    # Series
    lp_series_names = [lp_series.name for lp_series in lp_project.series]
    defined_series_names = set(project['series'].keys())
    missing_series_names = set(defined_series_names - set(lp_series_names))

    # Create missing series
    for series_name in missing_series_names:
        print '  Creating missing series %s...' % series_name
        lp_series = lp_project.newSeries(
            name=series_name,
            summary=project_all_series[series_name]['summary'])
        lp_series.status = project_all_series[series_name]['status']
        lp_series.lp_save()

    # Compute milestones
    project_all_milestones = {}
    for series_name, projet_series in list(project['series'].items()):
        projet_series['milestones'] = projet_series.get('milestones', {})
        series_milestones = {}
        for name, milestone in list(projet_series['milestones'].items()):
            milestone = milestone or dict()
            milestone.update({'series': series_name})
            series_milestones[name] = milestone
        project_all_milestones.update(series_milestones)

    # Milestones
    lp_milestone_names = [lp_milestone.name
                          for lp_milestone in lp_project.all_milestones]
    defined_milestone_names = set(project_all_milestones.keys())
    missing_milestone_names = set(defined_milestone_names -
                                  set(lp_milestone_names))

    # Create missing milestones
    for milestone_name in missing_milestone_names:
        print '  Creating missing milestone %s...' % milestone_name
        series_name = project_all_milestones[milestone_name]['series']
        lp_series = lp_project.getSeries(name=series_name)
        lp_milestone = lp_series.newMilestone(
            name=milestone_name,
            date_targeted=None,
            code_name=milestone_name)

    # TODO(mgagne) Sync milestone date_released

    # Development focus
    if lp_project.development_focus.name != project['development_focus']:
        print '  Wrong development focus: %s' % lp_project.development_focus.name
        print '  Updating development focus for %s...' % project['development_focus']
        lp_focus = lp_project.getSeries(name=project['development_focus'])
        lp_project.development_focus = lp_focus
        lp_project.lp_save()