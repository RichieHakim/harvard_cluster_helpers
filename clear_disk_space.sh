$HOMEDIR='/n/home03/rhakim'
# sudo

conda clean --all
# sudo journalctl --vacuum-size=200M
# flatpak uninstall --unused
# sudo flatpak repair
# sudo apt purge snapd

## remove and remake homedir / .cache / pip / http and http-v2
rm -R $HOMEDIR/.cache/pip/http
rm -R $HOMEDIR/.cache/pip/http-v2
mkdir $HOMEDIR/.cache/pip/http
mkdir $HOMEDIR/.cache/pip/http-v2

# ## Clear /tmp folder will delete all files and folders older than 10 days.
# sudo find /tmp -ctime +10 -exec rm -rf {} +

docker image prune --all

#################################
# conda activate env
# python -m pip cache purge
#################################