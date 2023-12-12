# FROM registry.access.redhat.com/ubi8/ubi
FROM rockylinux/rockylinux:8

RUN rpm -ivh https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm \
             https://download.fmi.fi/smartmet-open/rhel/8/x86_64/smartmet-open-release-21.3.26-2.el8.fmi.noarch.rpm

RUN dnf -y install dnf-plugins-core && \
    dnf -y module enable python38 && \
    dnf config-manager --set-enabled powertools && \
    dnf config-manager --setopt="epel.exclude=eccodes*" --save && \
    dnf -y --setopt=install_weak_deps=False install python38-pip python38-devel eccodes git && \
    dnf -y clean all && rm -rf /var/cache/dnf

RUN git clone https://github.com/fmidev/railtrack_temp_fcst.git

WORKDIR /railtrack_temp_fcst

RUN update-alternatives --set python3 /usr/bin/python3.8 && \
    python3 -m pip --no-cache-dir install -r requirements.txt
