#Requires -Version 5.1

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$InformationPreference = 'Continue'

# - https://stackoverflow.com/questions/43826134/why-is-the-bin-directory-called-differently-scripts-on-windows
py -m venv .venv

# - https://stackoverflow.com/questions/58627922/pip-install-upgrade-pip-fails-inside-a-windows-virtualenv-with-access-denie
.\.venv\Scripts\python -m pip install --upgrade pip

.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\pip install -r requirements-test.txt
