# Generateur d'attestation covid par Profile

Flask based generateur d'attestation covid


Basé sur https://github.com/tdopierre/AttestationNumeriqueCOVID-19

## Config
Regarder le fichier [`config.json.example`](./covid.json.example) et copier le a `config.json` avec les bon profiles

Mettre une image qui represent le profile dans static/profiles/${profile}.jpg (ou png), ${profile} et bien sure a remplacer au nom de profile.

## Install

Faire un virtualenv et installer les reqs :

```shell
python3 -m virtualenv .venv
.venv/bin/pip3 install -r requirements.txt
```

# Setup
```shell
cp etc/covidattestation.service /etc/systemd/system
```

Puis :

`vi /etc/systemd/system/covidattestation.service`

et configurer vers les bon path ou est votre appli

Ensuite faire un reverse proxy sur votre nginx ou autre, le mieux avec un chti
httpasswd et un SSL de configured :

```
    location /attestation {
        satisfy any;
        auth_basic "A base de popopop!"; #For Basic Auth
        auth_basic_user_file /etc/nginx/.htpasswd;  #For Basic Auth

        allow 192.168.0.0/24;
        allow 10.9.0.0/24;
        deny all;

        proxy_set_header  Host $host;
        proxy_set_header  X-Real-IP $remote_addr;
        proxy_set_header  X-Forwarded-Proto https;
        proxy_pass_header X-Transmission-Session-Id;
        proxy_set_header  X-Forwarded-For $remote_addr;
        proxy_set_header  X-Forwarded-Host $remote_addr;

        proxy_pass http://127.0.0.1:8000;
    }
```
