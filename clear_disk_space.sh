# sudo

conda clean --all
# sudo journalctl --vacuum-size=200M
# flatpak uninstall --unused
# sudo flatpak repair
# sudo apt purge snapd

## remove and remake homedir / .cache / pip / http and http-v2
rm -R /n/home03/rhakim/.cache/pip/http
rm -R /n/home03/rhakim/.cache/pip/http-v2
mkdir /n/home03/rhakim/.cache/pip/http
mkdir /n/home03/rhakim/.cache/pip/http-v2

# ## Clear /tmp folder will delete all files and folders older than 10 days.
# sudo find /tmp -ctime +10 -exec rm -rf {} +

docker image prune --all

#################################
# conda activate env
# python -m pip cache purge
#################################


rm -R /n/home03/rhakim/wandb