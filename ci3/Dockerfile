FROM composer:2 AS dependencies
WORKDIR /build
COPY composer.json .
RUN composer install --no-dev --prefer-dist --no-interaction
FROM php:8.2-apache
RUN apt-get update && apt-get install -y --no-install-recommends libcurl4-openssl-dev && rm -rf /var/lib/apt/lists/* && docker-php-ext-install mysqli pdo_mysql curl && a2enmod rewrite
COPY --from=dependencies /build/vendor /var/www/vendor
COPY application /var/www/html/application
COPY public/index.php public/.htaccess /var/www/html/
EXPOSE 80
