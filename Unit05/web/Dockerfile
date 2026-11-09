# Book&Ride - Unit 05 - Apache 2 with HTTPS (DEVOP2 U11 sheets 21 and 22, in a
# container instead of a VM). The official image keeps its config in
# /usr/local/apache2/conf: we switch on the modules the sheets enable with
# a2enmod (ssl, rewrite) and include our own virtual hosts.
FROM httpd:2.4
RUN sed -i \
      -e 's/^#\(LoadModule ssl_module\)/\1/' \
      -e 's/^#\(LoadModule socache_shmcb_module\)/\1/' \
      -e 's/^#\(LoadModule rewrite_module\)/\1/' \
      -e 's/^#\(LoadModule headers_module\)/\1/' \
      /usr/local/apache2/conf/httpd.conf \
 && echo 'Include conf/extra/bookride.conf' >> /usr/local/apache2/conf/httpd.conf
COPY bookride.conf /usr/local/apache2/conf/extra/bookride.conf
COPY sites/ /usr/local/apache2/htdocs/
# no curl in the image: bash opens a TCP connection to port 80
HEALTHCHECK --interval=5s --timeout=3s --retries=10 CMD bash -c '</dev/tcp/127.0.0.1/80'
