<?php
defined('BASEPATH') OR exit('No direct script access allowed');
$active_group = 'default';
$query_builder = TRUE;
$db_pass = getenv('DB_PASSWORD');
if (!$db_pass || $db_pass === 'change_me_local_only') { $db_pass = 'atlas_dev_password'; }
$db['default'] = ['dsn'=>'','hostname'=>getenv('DB_HOST') ?: 'mysql','username'=>getenv('DB_USER') ?: 'atlas','password'=>$db_pass,'database'=>'project_atlas','dbdriver'=>'mysqli','dbprefix'=>'','pconnect'=>FALSE,'db_debug'=>FALSE,'cache_on'=>FALSE,'cachedir'=>'','char_set'=>'utf8mb4','dbcollat'=>'utf8mb4_unicode_ci','swap_pre'=>'','encrypt'=>FALSE,'compress'=>FALSE,'stricton'=>FALSE,'failover'=>[],'save_queries'=>FALSE];
