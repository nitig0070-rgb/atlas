<?php
define('ENVIRONMENT', 'production');
define('SELF', pathinfo(__FILE__, PATHINFO_BASENAME));
define('FCPATH', __DIR__ . DIRECTORY_SEPARATOR);
define('BASEPATH', dirname(__DIR__) . '/vendor/codeigniter/framework/system/');
define('SYSDIR', 'system');
define('APPPATH', __DIR__ . '/application/');
define('VIEWPATH', APPPATH . 'views/');
// CodeIgniter 3.1.13 predates PHP 8.2's dynamic-property deprecations.
// Keep those compatibility notices out of production responses while leaving
// warnings and errors enabled for the framework's normal error handling.
if (ENVIRONMENT === 'production') {
    error_reporting(E_ALL & ~E_DEPRECATED & ~E_USER_DEPRECATED);
    ini_set('display_errors', '0');
}
require_once BASEPATH . 'core/CodeIgniter.php';
