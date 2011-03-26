from fabric.api import local, settings, abort, run, cd, lcd, env
from fabric.contrib.console import confirm
from datetime import date

def build(stub, branch='develop', domain='pinkgators.com'):
    # parse project stub (in /var/aegir/build/project.build) 
    #   to get profile repo and clone it to tmp
    repo = local('php get_profile_repo.php %s' % stub, True)
    stub_id = local('php get_profile_name.php %s' % stub, True)
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
    local('php /var/aegir/drush/drush.php @hostmaster hosting-dispatch')
    local('drush @hostmaster hosting-import @platform_%s' % platform_id)

    # if @project-dev.devserver.com exists
    with settings(warn_only=True):
        existing_site = local('drush sa |grep "%s"' % site_uri, True)
    if existing_site:
        local('php /var/aegir/drush/drush.php @hostmaster hosting-task @platform_%s verify' % platform_id)
        local('php /var/aegir/drush/drush.php @hostmaster hosting-dispatch')
        local("php /var/aegir/drush/drush.php @%s provision-migrate '@platform_%s'" % (site_uri, platform_id))
        local("php /var/aegir/drush/drush.php --uri='%s' --platform='@platform_%s' --root='/var/aegir/platforms/%s/%s' --profile='%s' provision-save '@%s'" % (site_uri, platform_id, stub_id, platform_id, stub_id, site_uri))
        backup = local('ls -t /var/aegir/backups/%s-* | head -1' % (stub_id), True)
        local("php /var/aegir/drush/drush.php --old_uri='%s' @%s provision-deploy %s" % (site_uri, site_uri, backup))
        local("php /var/aegir/drush/drush.php @hostmaster hosting-import @%s" % (site_uri))
        local("php /var/aegir/drush/drush.php @hostmaster hosting-task @platform_%s verify" % platform_id)
        local("php /var/aegir/drush/drush.php @hostmaster hosting-task @%s verify" % site_uri)
    else:
        print "provision site"
        #migrate @project-dev.devserver.com to @platform_projectSHA1
    #  local('php /var/aegir/drush/drush.php @%s provision-migrate %s -vd' % (site_uri, path_to_platform))
    #else:
      # provision-site @project-dev.devserver.com
    #  local('php /var/aegir/drush/drush.php provision-save --uri="%s" --platform="@platform_%s" "@%s"' % (site_uri, platform_id, site_uri))
    #  local('php /var/aegir/drush/drush.php provision-install @%s' % site_uri)

    # clean up old platform(s)
    #
