from fabric.api import local, settings, abort, run, cd, lcd, env
from fabric.contrib.console import confirm
from datetime import date

def build(stub, branch='develop', domain='pinkgators.com'):
    # parse project stub (in /var/aegir/build/project.build) 
    #   to get profile repo and clone it to tmp
    repo = local('./get_profile_repo.php %s' % stub, True)
    stub_id = local('./get_profile_name.php %s' % stub, True)
    site_uri = stub_id + "-dev." + domain

    # get sha1 of latest commit
    # build id is now project-SHA1
    # remove tmp checkout
    tmp_repo = '/tmp/' + stub_id
    local('rm -rf %s' % (tmp_repo))
    local('git clone -b %s %s %s' % (branch, repo, tmp_repo))
    with lcd(tmp_repo):
        commit_id = local('git log --format="%h" -1', True)
    local('rm -rf %s' % (tmp_repo))

    # if @platform_projectSHA1 exits quit
    platform_id = stub_id + commit_id
    with settings(warn_only=True):
        existing_platform = local('drush sa |grep "platform_%s"' % platform_id, True)
        if (existing_platform):
            exit("PLATFORM EXISTS")
    print "Platform to be built: @platform_" + platform_id

    # provision-save @platform_projectSHA1 =>
    #   name (project-SHA1),
    #   publish path (/var/platforms/project/project-SHA1),
    #   make (/var/aegir/build/project.build)
    # provision-verify @platform_projectSHA1
    # hosting-import @platform_projectSHA1
    path_to_platform = "/var/aegir/platforms/" + stub_id + "/" + platform_id
    makefile = stub
    local('drush provision-save @platform_%s --context_type=platform \
                --root="%s" --makefile="%s"' % (platform_id, path_to_platform, makefile))
    local('drush provision-verify @platform_%s' % platform_id)
    local('drush hosting-import @platform_%s' % platform_id)

    # if @project-dev.devserver.com exists
    existing_site = local('drush sa |grep "%s"' % site_uri, True)
    if exisiting_site:
      # migrate @project-dev.devserver.com to @platform_projectSHA1
      local('php /var/aegir/drush/drush.php provision-migrate %s %s' % (site_uri, path_to_platform))
    else:
      # provision-site @project-dev.devserver.com
      local('php /var/aegir/drush/drush.php provision-save --uri="%s" --platform="@platform_%s" "@%s"' % (site_uri, platform_id, site_uri))
      local('php /var/aegir/drush/drush.php provision-install @%s' % site_uri)

    # clean up old platform(s)
    #
