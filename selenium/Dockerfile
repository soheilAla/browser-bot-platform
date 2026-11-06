FROM selenium/standalone-chrome:4.51.0-20261010

USER root
# Replace chromedriver $cdc_ fingerprint string with harmless dog_ of equal byte length
RUN perl -pi -e 's/cdc_/dog_/g' /usr/bin/chromedriver

USER 1200
