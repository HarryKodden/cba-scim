
FROM ubuntu:latest AS builder

RUN apt update
RUN apt install -y apt-transport-https locales ca-certificates vim
RUN apt install -y rsyslog  openssh-server pamtester libcurl4-gnutls-dev
RUN apt install -y libsasl2-dev libldap2-dev ldap-utils 
RUN apt install -y python3 python3-pip

ADD requirements.txt .
RUN pip install -r requirements.txt && rm requirements.txt

COPY ./sync /root/sync

COPY ./entrypoint.sh /
RUN chmod o+x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
