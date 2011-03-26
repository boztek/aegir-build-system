#!env php
<?php

/**
 * Print out profile repo parsed from a drush make build stub
 */

define('DRUSH_BASE_PATH', '/usr/local/drush');
define('DRUSH_MAKE_PATH', '/Users/boris/.drush/drush_make');
require_once DRUSH_BASE_PATH . '/includes/drush.inc';
require_once DRUSH_BASE_PATH . '/includes/context.inc';
require_once DRUSH_BASE_PATH . '/includes/exec.inc';
require_once DRUSH_MAKE_PATH . '/drush_make.drush.inc';

$info = drush_make_parse_info_file($argv[1]);
foreach ($info['projects'] as $name => $prj) {
  if ($prj['type'] == 'profile') {
    print $name . "\n";
    break;
  }
}
