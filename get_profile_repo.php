<?php

/**
 * Print out profile repo parsed from a drush make build stub
 */

define('DRUSH_BASE_PATH', '/var/aegir/drush');
define('DRUSH_MAKE_PATH', '/var/aegir/.drush/drush_make');
require_once DRUSH_BASE_PATH . '/includes/drush.inc';
require_once DRUSH_BASE_PATH . '/includes/context.inc';
// require_once DRUSH_BASE_PATH . '/includes/exec.inc';
require_once DRUSH_MAKE_PATH . '/drush_make.drush.inc';

$info = drush_make_parse_info_file($argv[1]);
foreach ($info['projects'] as $prj) {
  if ($prj['type'] == 'profile') {
    print($prj['download']['url'] . "\n");
    break;
  }
}
