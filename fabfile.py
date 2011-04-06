from fabric.api import local, settings, abort, run, cd, lcd, env
from fabric.contrib.console import confirm
from datetime import date

def release(stub, tag, site_uri, sync_uri):
    """Build a platform from a tag and sync db and files from another site"""
    build(stub, release=tag)
    sync_site(sync_uri, site_uri)

def provision_site(site_uri, platform_id, app_id):
    """If site_uri exists migrate to platform_id else install new site"""
    with settings(warn_only=True):
        existing_site = local('drush sa |grep "%s"' % site_uri, True)
    if existing_site:
        local('php /var/aegir/drush/drush.php @hostmaster hosting-task @platform_%s verify' % platform_id)
        local('php /var/aegir/drush/drush.php @hostmaster hosting-dispatch')
        local("php /var/aegir/drush/drush.php @%s provision-migrate '@platform_%s'" % (site_uri, platform_id))
        local("php /var/aegir/drush/drush.php --uri='%s' --platform='@platform_%s' --root='/var/aegir/platforms/%s/%s' --profile='%s' provision-save '@%s'" % (site_uri, platform_id, app_id, platform_id, app_id, site_uri))
        backup = local('ls -t /var/aegir/backups/%s-* | head -1' % (app_id), True)
        local("php /var/aegir/drush/drush.php --old_uri='%s' @%s provision-deploy %s" % (site_uri, site_uri, backup))
        local("php /var/aegir/drush/drush.php @hostmaster hosting-import @%s" % (site_uri))
        local("php /var/aegir/drush/drush.php @hostmaster hosting-task @platform_%s verify" % platform_id)
        local("php /var/aegir/drush/drush.php @hostmaster hosting-task @%s verify" % site_uri)
    else:
        # provision-site @site_uri
        local('php /var/aegir/drush/drush.php provision-save --uri="%s" \
            --platform="@platform_%s" "@%s"' % 
            (site_uri, platform_id, site_uri))
        local('php /var/aegir/drush/drush.php provision-install @%s' % 
            (site_uri))

def build_platform(buildfile, platform_id, app_id):
    """Build a platform from a build level drush make file using provision"""
    # exit if platform exists
    with settings(warn_only=True):
        existing_platform = local('drush sa |grep "platform_%s"' % platform_id, True)
        if (existing_platform):
            exit("PLATFORM EXISTS")
        else
            print "Platform to be built: @platform_" + platform_id
    path_to_platform = "/var/aegir/platforms/" + app_id + "/" + platform_id
    local('drush provision-save @platform_%s --context_type=platform \
            --root="%s" --makefile="%s"' % 
            (platform_id, path_to_platform, buildfile))
    local('drush provision-verify @platform_%s' % platform_id)
    local('php /var/aegir/drush/drush.php @hostmaster hosting-dispatch')
    local('drush @hostmaster hosting-import @platform_%s' % platform_id)

def build(stub, branch=None, site_uri=None, migrate=True, release=None):
    repo = local('php get_profile_repo.php %s' % stub, True)
    app_id = local('php get_profile_name.php %s' % stub, True)
    if (not branch):
        branch = local('php get_profile_branch.php %s' % stub, True)
    # build id is now project-SHA1 where SHA1 is head of branch
    tmp_repo = '/tmp/' + app_id
    local('rm -rf %s' % (tmp_repo))
    local('git clone -b %s %s %s' % (branch, repo, tmp_repo))
    with lcd(tmp_repo):
        commit_id = local('git log --format="%h" -1', True)
    local('rm -rf %s' % (tmp_repo))
    # if build of this commit already exists quit
    platform_id = app_id + commit_id
    build_platform(stub, platform_id, app_id)
    # migrate site
    if (site_uri and migrate):
        provision_site(site_uri, platform_id, app_id)
