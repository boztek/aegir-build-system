from fabric.api import local, settings, abort, run, cd, lcd, env
from fabric.contrib.console import confirm
from datetime import datetime, date
import json


def test():
	print __get_alias_variable()

def __get_alias_variable(alias='hostmaster', variable='db_server'):
	return __read_alias(alias)[variable]

def __read_alias(alias='hostmaster'):
    alias_file = "/var/aegir/.drush/%s.alias.drushrc.php" % alias
    json_array = local("/usr/bin/php -r 'require(\"%s\"); print json_encode($aliases);'" % alias_file, True)
    return json.loads(json_array)[alias]


def release(repo, tag, site_uri, sync_uri=None):
    """Build a platform from a tag, migrate the site and optionally sync db and files from another site"""
    build(repo, tag, site_uri)
    if (sync_uri):
        sync_site(sync_uri, site_uri)
    local('php /var/aegir/drush/drush.php @%s cache-clear all' % site_uri)
    local('php /var/aegir/drush/drush.php @%s cache-clear all' % site_uri)
    local('php /var/aegir/drush/drush.php @%s features-list' % site_uri)
    local('php /var/aegir/drush/drush.php --yes @%s features-revert-all' % site_uri)
    local('php /var/aegir/drush/drush.php @%s cache-clear all' % site_uri)

def sync_site(source_site, dest_site):
    """Delete dest_site instance and clone from source_site with provision"""
    platform = __get_alias_variable(dest_site, 'platform')
    delete_site(dest_site)
    local('/var/aegir/drush/drush.php @%s provision-clone @%s %s' %
        (source_site, dest_site, platform))
    # Update site context object to refer to correct db server
    db_server = __get_alias_variable(dest_site, 'db_server')
    local('php /var/aegir/drush/drush.php --db_server="%s" provision-save \
        "@%s"' % (db_server, dest_site))
    # Redeploy from backup this time with correct db server
    local('php /var/aegir/drush/drush.php --old_uri="%s" "@%s" provision-deploy `ls -t /var/aegir/backups/%s* |head -1`' % 
        (source_site, dest_site, source_site))
    # Verify destination platform to import site into aegir front end
    local('php /var/aegir/drush/drush.php @hostmaster hosting-task \
        %s verify'% (platform))
    local('php /var/aegir/drush/drush.php @hostmaster hosting-dispatch')


def delete_site(site_uri):
    """Disable and delete a site instance after making a backup"""
    local('php /var/aegir/drush/drush.php @%s provision-backup' % site_uri)
    local('php /var/aegir/drush/drush.php @hostmaster \
        hosting-task @%s disable' % site_uri)
    local('php /var/aegir/drush/drush.php @hostmaster hosting-dispatch')
    local('php /var/aegir/drush/drush.php @hostmaster \
        hosting-task @%s delete' % site_uri)
    local('php /var/aegir/drush/drush.php @hostmaster hosting-dispatch')


def _provision_new_site(site_uri, platform_id, app_id, db_server_id, email):
    """Provision a new site instance and import into hostmaster front end"""
    local('php /var/aegir/drush/drush.php provision-save @%s --context_type=site --uri=%s --platform=@platform_%s --db_server=@server_%s --client_email=%s --profile=%s' % (site_uri,site_uri,platform_id,db_server_id,email,app_id))
    local('php /var/aegir/drush/drush.php @%s provision-install --debug' % (site_uri))
    local('php /var/aegir/drush/drush.php @%s provision-verify --debug' % (site_uri))
    local('php /var/aegir/drush/drush.php @hostmaster hosting-task @platform_%s verify' % (platform_id))
    local('php /var/aegir/drush/drush.php @hostmaster hosting-dispatch')

def provision_site(site_uri, platform_id, app_id, db_server_id=None, email='email@client.com'):
    """If site_uri exists migrate to platform_id else install new site"""
    with settings(warn_only=True):
        existing_site = local('php /var/aegir/drush/drush.php sa |grep "%s"' % site_uri, True)
    if existing_site:
        db_server = __get_alias_variable(site_uri, 'db_server')
        local('php /var/aegir/drush/drush.php @hostmaster hosting-task @platform_%s verify' % platform_id)
        local('php /var/aegir/drush/drush.php @hostmaster hosting-dispatch')
        local("php /var/aegir/drush/drush.php @%s provision-migrate '@platform_%s'" % (site_uri, platform_id))
        backup = local('ls -t /var/aegir/backups/%s-* | head -1' % (site_uri), True)
        print "Deploying from backup: " + backup
        local("php /var/aegir/drush/drush.php --old_uri='%s' @%s provision-deploy %s" % (site_uri, site_uri, backup))
        local('php /var/aegir/drush/drush.php provision-save @%s --context_type=site --uri=%s --platform=@platform_%s --db_server=%s --profile=%s' % (site_uri,site_uri,platform_id,db_server,app_id))
        local("php /var/aegir/drush/drush.php @hostmaster hosting-import @%s" % (site_uri))
        local("php /var/aegir/drush/drush.php @hostmaster hosting-task @platform_%s verify" % platform_id)
        local("php /var/aegir/drush/drush.php @hostmaster hosting-task @%s verify" % site_uri)
    else:
        # provision-site @site_uri
        if (not db_server_id):
            _provision_new_site(site_uri, platform_id, app_id, 'localhost', email)
        else:
            _provision_new_site(site_uri, platform_id, app_id, db_server_id, email)


def build_platform(buildfile, platform_id, app_id, server):
    """Build a platform from a build level drush make file using provision"""
    # exit if platform exists
    with settings(warn_only=True):
        existing_platform = local('php /var/aegir/drush/drush.php sa |grep "platform_%s"' % platform_id, True)
        if (existing_platform):
            exit("PLATFORM EXISTS")
        else:
            print "Platform to be built: @platform_" + platform_id
    path_to_platform = "/var/aegir/platforms/" + app_id + "/" + platform_id
    local('php /var/aegir/drush/drush.php provision-save @platform_%s --context_type=platform --root="%s" --makefile="%s" --web_server="%s"' % 
            (platform_id, path_to_platform, buildfile, server))
    local('php /var/aegir/drush/drush.php provision-verify @platform_%s --debug' % platform_id)
    local('php /var/aegir/drush/drush.php @hostmaster hosting-dispatch')
    local('php /var/aegir/drush/drush.php @hostmaster hosting-import @platform_%s' % platform_id)
    local('php /var/aegir/drush/drush.php @hostmaster hosting-task @platform_%s verify' % platform_id)
    local('php /var/aegir/drush/drush.php @hostmaster hosting-dispatch')


def build(git_url, branch='develop', site_uri=None, server_id=None):
    """Check out source code and extract platform build stub from repo and build platform with provision"""
    tmp_repo = '/tmp/provision_platform_src_' + datetime.now().strftime('%Y%m%d%H%M%S')
    local('rm -rf %s' % (tmp_repo))
    local('git clone %s %s' % (git_url, tmp_repo))
    with lcd(tmp_repo):
        # checkout either a tag or branch
        local('git checkout %s' % (branch))
        # assume only one .build file in source code root
        app_id = local("ls |egrep '\.build$' |head -1 |cut -d'.' -f1", True)
        commit_id = local('git log --format="%h" -1', True)
    # At the moment we keep only one build stub at any one time
    local('mkdir -pv /var/aegir/builds/%s' % app_id)
    local('cp %s/%s.build /var/aegir/builds/%s/%s.build' % 
        (tmp_repo, app_id, app_id, app_id))
    local('rm -rf %s' % (tmp_repo))
    platform_id = app_id + commit_id
    stub = '/var/aegir/builds/%s/%s.build' % (app_id, app_id)
    p_server = None
    if (server_id):
        p_server = '@server_' + server_id
    elif (site_uri):
        pid = __get_alias_variable(site_uri, 'platform')
        pid = pid[1:]
        p_server = __get_alias_variable(pid, 'web_server')
    if (p_server):
        print "Building '" +app_id+ "' on server '" +p_server+ "'"
        build_platform(stub, platform_id, app_id, p_server)
        with settings(warn_only=True):
            if (branch == 'develop'):
                with lcd('/var/aegir/platforms/%s' % app_id):
                    local('rm dev.%s' % app_id)
                    local('ln -s %s dev.%s' % (platform_id, app_id))
    else:
        exit('No server details provided either directly or through site default')
    # migrate site
    if (site_uri):
        provision_site(site_uri, platform_id, app_id)
        local('php /var/aegir/drush/drush.php @%s cache-clear all' % site_uri)
        local('php /var/aegir/drush/drush.php @%s cache-clear all' % site_uri)
        local('php /var/aegir/drush/drush.php --yes @%s features-revert-all' % site_uri)


