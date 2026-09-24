## Host the rdgen server with docker

1. First you will need to fork this repo on github
2. Next, setup a A Github fine-grained access token with permissions for your rdgen
   repository:
    * login to your github account  
    * click on your profile picture at the top right, click Settings  
    * at the bottom of the left panel, click Developer Settings  
    * click Personal access tokens  
    * click Fine-grained tokens  
    * click Generate new token  
    * give a token name, change expiration to whatever you want  
    * under Repository access, select Only select repositories, then pick your
      rdgen repo  
    * give Read and Write access to actions and workflows  
    * You might have to go to: https://github.com/USERNAME/rdgen/actions and hit green Enable Actions button so it works.
3. Next, login to your Github account, go to your rdgen repo page (https://github.com/USERNAME/rdgen)
   * Click on Settings
   * In the left pane, click on Secrets and variables, then click Actions
   * Now click New repository secret
   * Set the Name to GENURL
   * Set the Secret to https://rdgen.hostname.com (or whatever your server will be accessed from)
   * Now click New repository secret again
   * Set the Name to ZIP_PASSWORD
   * Set the Secret to any password you want (use this in the next step as well) - generate a password by running: ```python3 -c 'import secrets; print(secrets.token_hex(100))'```
   * Add `RDGEN_UPLOAD_TOKEN` as a separate long random secret. Configure the
     same value in the RDGen container environment; it authenticates artifact
     uploads from GitHub Actions.
4. Now download the docker-compose.yml file and fill in the environment variables:
  * SECRET_KEY="your secret key" - generate a secret key by running: ```python3 -c 'import secrets; print(secrets.token_hex(100))'```
  * GHUSER="your github username"  
  * GHBEARER="your fine-grained access token"  
  * GENURL="https://rdgen.hostname.com" - the full public origin of RDGen;
    it is also used as the default trusted CSRF origin
  * ZIP_PASSWORD="the same password that you entered as a github secret"
  * PROTOCOL="https" *optional - defaults to "https", change to "http" if you need to
  * REPONAME="rdgen" *optional - defaults to "rdgen", change this if you renamed the repo when you forked it
  * RDGEN_UPLOAD_TOKEN="the same value as the GitHub Actions secret"
  * RDGEN_DASHBOARD_TOKEN="a different long random token shared only with RDBK"
  * RDBK_HOST_REGISTRATION_SECRET="the same long random bootstrap secret as RDBK";
    this is required for managed Windows Helpdesk builds and must not be stored
    in Git
  * RDBK_WINDOWS_SIGNER_SUBJECT="the expected Authenticode certificate subject";
    strongly recommended once Artifact Signing is enabled
  * CSRF_TRUSTED_ORIGINS="https://rdgen.hostname.com" *optional - space- or
    comma-separated list used only when RDGen is published under more than one
    origin; otherwise `GENURL` is used automatically
  * TRUST_X_FORWARDED_PROTO="true" *optional - keep enabled for an HTTPS
    reverse proxy; the proxy must send `X-Forwarded-Proto`
5. Create the persistent, recoverable artifact trash and make it writable by
   the container user: `mkdir -p artifact_trash && chown 1000:1000 artifact_trash`.
   Keep the `./artifact_trash:/opt/rdgen/artifact_trash` bind mount from the
   example Compose file and include this directory in host backups.
6. Now just run ```docker compose up -d```


## Use a self hosted github runner for faster client generation (Windows only right now)

1. First you need to set up a Windows computer that can build rustdesk
2. Once you can build rustdesk, follow github instructions for setting up a self hosted github runner
3. Now you need to add an environment variable SH_SECRET, which has a key/password that you will need to send to the server
4. Save a json configuration file from your rdgen web ui
5. Use the [rdgen-cli] (https://github.com/AlekseyLapunov/rdgen-cli) to submit your json configuration with the added key "sh_secret_field" with the value matching your SH_SECRET

## Sign Windows builds with Azure Artifact Signing

The Windows workflows are prepared for
[Azure Artifact Signing](https://learn.microsoft.com/azure/artifact-signing/).
Signing is fail-closed when enabled, but remains disabled until the repository
variable `AZURE_ARTIFACT_SIGNING_ENABLED` is explicitly set to `true`.

1. Complete the Artifact Signing identity validation, create a signing account
   and a public-trust certificate profile.
2. Create a Microsoft Entra application or managed identity with a federated
   GitHub Actions credential restricted to this repository and the intended
   branch/environment. Grant it only the Artifact Signing certificate profile
   signer role for the selected profile.
3. Add these GitHub Actions secrets:
   - `AZURE_CLIENT_ID`
   - `AZURE_TENANT_ID`
   - `AZURE_SUBSCRIPTION_ID`
   - `AZURE_ARTIFACT_SIGNING_ENDPOINT`
   - `AZURE_ARTIFACT_SIGNING_ACCOUNT_NAME`
   - `AZURE_ARTIFACT_SIGNING_CERTIFICATE_PROFILE_NAME`
4. Leave `AZURE_ARTIFACT_SIGNING_ENABLED` unset or `false` while validation is
   pending. Builds continue to work and are reported as unsigned.
5. After validation, run a test build and verify the signer and timestamp. Only
   then set the repository variable `AZURE_ARTIFACT_SIGNING_ENABLED=true`.

The workflow signs runtime EXE/DLL files before portable packing and signs the
final EXE/MSI artifacts afterwards. Every signing stage is verified and aborts
the build if a signature is missing or invalid. Authentication uses GitHub OIDC;
no PFX file or long-lived client secret is stored in the repository.


## Host manually:

1. A Github account with a fork of this repo  
2. A Github fine-grained access token with permissions for your rdgen
   repository:
    * login to your github account  
    * click on your profile picture at the top right, click Settings  
    * at the bottom of the left panel, click Developer Settings  
    * click Personal access tokens  
    * click Fine-grained tokens  
    * click Generate new token  
    * give a token name, change expiration to whatever you want  
    * under Repository access, select Only select repositories, then pick your
      rdgen repo  
    * give Read and Write access to actions and workflows  
    * You might have to go to: https://github.com/USERNAME/rdgen/actions and hit green Enable Actions button so it works.
3. Setup environment variables/secrets:
    * environment variables on the server running rdgen:  
        * GHUSER="your github username"  
        * GHBEARER="your fine-grained access token"  
        * PROTOCOL="https" *optional - defaults to "https", change to "http" if you need to
        * REPONAME="rdgen" *optional - defaults to "rdgen", change this if you renamed the repo when you forked it
    * github secrets (setup on your github account for your rdgen repo):  
        * GENURL="example.com:8000"  *this is the domain and port that you are
          running rdgen on, needs to be accessible on the internet, depending
          on how you have this setup the port may not be needed  

```
# Open to the directory you want to install rdgen (change /opt to wherever you want)  
cd /opt

# Clone your rdgen repo, change bryangerlach to your github username
git clone https://github.com/bryangerlach/rdgen.git

# Open the rdgen directory
cd rdgen

# Setup a python virtual environment called rdgen
python -m venv .venv

# Activate the python virtual environment 
source .venv/bin/activate

# Install the python dependencies
pip install -r requirements.txt

# Setup the database
python manage.py migrate

# Run the server, change 8000 with whatever you want
python manage.py runserver 0.0.0.0:8000
```

open your web browser to yourdomain:8000

Use nginx, Caddy, Traefik, Nginx Proxy Manager, or an equivalent TLS reverse
proxy. Preserve the original `Host` header and send
`X-Forwarded-Proto: https`. Set `GENURL` to the same full public HTTPS origin;
otherwise Django will reject form submissions with a CSRF 403 response.

### To autostart the server on boot, you can set up a systemd service called rdgen.service

replace user, group, and port if you need to  replace /opt with wherever you
have installed rdgen  save the following file as
/etc/systemd/system/rdgen.service, and make sure to change GHUSER, GHBEARER

```
[Unit]
Description=Rustdesk Client Generator
[Service]
Type=simple
LimitNOFILE=1000000
Environment="GHUSER=yourgithubusername"
Environment="GHBEARER=yourgithubtoken"
PassEnvironment=GHUSER GHBEARER
ExecStart=/opt/rdgen/.venv/bin/python3 /opt/rdgen/manage.py runserver 0.0.0.0:8000
WorkingDirectory=/opt/rdgen/
User=root
Group=root
Restart=always
StandardOutput=file:/var/log/rdgen.log
StandardError=file:/var/log/rdgen.error
# Restart service after 10 seconds if node service crashes
RestartSec=10
[Install]
WantedBy=multi-user.target
```

then run this to enable autostarting the service on boot, and then start it
manually this time:

```
sudo systemctl enable rdgen.service
sudo systemctl start rdgen.service
```
and to get the status of the server, run:
```
sudo systemctl status rdgen.service
```
