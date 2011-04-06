from fabric.api import local, settings, abort, run, cd, lcd, env
from fabric.contrib.console import confirm
from datetime import datetime, date

def release(repo, tag, site_uri, sync_uri):
    """Build a platform from a tag and sync db and files from another site"""
    build(repo, tag, site_uri)
    if (sync_uri):
        sync_site(sync_uri, site_uri)

def sync_site(source_site, dest_site):
    """Delete dest_site instance and clone from source_site with provision"""
    platform_id = get_platform()
    delete_site(dest_site)
    # /var/aegir/drush/drush.php @$SOURCE_URL provision-clone @$DEST_URL @$DEST_PLATFORM
    local('/var/aegir/drush/drush.php @%s provision-clone @%s @%s' %
        (source_site, dest_site, platform_id))
    # Update site context object to refer to correct db server
    # /var/aegir/drush/drush.php --db_server=@$DEST_DB provision-save @$DEST_URL
    # Redeploy from backup this time with correct db server
    # /var/aegir/drush/drush.php --old_uri="$SOURCE_URL" "@$DEST_URL" provision-deploy `ls -t /var/aegir/backups/$SOURCE_URL* |head -1`
    # Verify destination platform to import site into aegir front end
    # /var/aegir/drush/drush.php @hostmaster hosting-task @$DEST_PLATFORM verify

def delete_site(site_uri):
    """Disable and delete a site instance after making a backup"""
    local('php /var/aegir/drush/drush.php @%s provision-backup' % site_uri)
    local('php /var/aegir/drush/drush.php @hostmaster \
        hosting-task @%s disable' % site_uri)
    local('php /var/aegir/drush/drush.php @hostmaster hosting-dispatch')
    local('php /var/aegir/drush/drush.php @hostmaster \
        hosting-task @%s delete' % site_uri)
    local('php /var/aegir/drush/drush.php @hostmaster hosting-dispatch')

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

def build(repo, branch='develop', site_uri=None, release=None):
    """Check out source code and extract platform build stub from repo and build platform with provision"""
    tmp_repo = '/tmp/provision_platform_src_' + 
        datetime.now().strftime('%Y%m%d%H%M%S')
    local('rm -rf %s' % (tmp_repo))
    local('git clone %s %s' % (repo, tmp_repo))
    with lcd(tmp_repo):
        local('git checkout %s' % (branch))
        # assume only one .build file in source code root
        app_id = local('ls |grep build |head -1 |cut -d'.' -f1')
        # if stub:
        #     app_id = local('php get_profile_name.php %s' % (stub), True)
        commit_id = local('git log --format="%h" -1', True)
app_id))
    # At the moment we keep only one build stub at any one time
    local('mkdir -pv /var/aegir/builds/%s' % app_id)
    local('cp %s/%s.build /var/aegir/builds/%s/%s.build' % 
        (temp_repo, app_id, app_id, app_id))
    local('rm -rf %s' % (tmp_repo))
    platform_id = app_id + commit_id
    stub = '/var/aegir/builds/%s/%s.build' % (app_id, app_id)
    build_platform(stub, platform_id, app_id)
    # migrate site
    if (site_uri):
        provision_site(site_uri, platform_id, app_id)
