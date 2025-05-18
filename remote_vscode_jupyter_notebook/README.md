How to keep a persistent remote Jupyter kernel that can be reconnected to.

---

### Overview

1.	Launch a VS Code Remote Tunnel via sbatch.
2.	Open a terminal inside the tunnel window.
3.	Start a detached tmux session and run Jupyter there.
4.	Forward the Jupyter port ( 8888 ) in VS Code’s Ports panel.
5.	Tell VS Code’s Jupyter extension to use “Existing Server” → http://localhost:8888/?token=….
6.	Reconnect any time; the kernel—and all variables—stay put.

---

### Prerequisites

Cluster & VS Code
- An `sbatch` template that starts code tunnel on a compute node (Harvard/FASRC recipe).
```bash
#!/bin/bash
#SBATCH --account=kempner_bsabatini_lab  # The account name for the job.
#SBATCH --partition=kempner              # Partition (job queue)
#SBATCH --gres=gpu:1                     # Number of GPUs
#SBATCH -c 16                            # Number of cores on one node
#SBATCH -n 1                             # Number of nodes
#SBATCH --mem=240GB                      # Memory pool for all cores
#SBATCH --time=0-16:00:00                # Runtime in D-HH:MM:SS

set -o errexit -o nounset -o pipefail
MY_SCRATCH=$(TMPDIR=/scratch mktemp -d)
echo $MY_SCRATCH

# 0) Start (or re-use) a tmux session named "jupyter" on the compute node
ENV="fr"
SESSION="jupyter"
if ! tmux has-session -t "${SESSION}" 2>/dev/null; then
  echo "🔹 Creating new tmux session '${SESSION}' and launching Jupyter"
  source activate ${ENV}
  tmux new -s "${SESSION}" -d \
    "jupyter lab \
       --no-browser \
       --ip=127.0.0.1 \
       --port=8888 \
       --NotebookApp.token='MYTOKEN'"
else
  echo "🔹 tmux session '${SESSION}' already exists—skipping launch"
fi

# 1) Download & unpack the VS Code CLI
curl -Lk 'https://code.visualstudio.com/sha/download?build=stable&os=cli-alpine-x64' \
  | tar -C $MY_SCRATCH -xzf -

# 2) Authenticate the CLI once
VSCODE_CLI_DISABLE_KEYCHAIN_ENCRYPT=1 \
  $MY_SCRATCH/code tunnel user login --provider github

# 3) Ensure VS Code serves your 'scripts' folder  
cd $HOME/scripts

# 4) Launch the tunnel **with** an attached workspace  
$MY_SCRATCH/code tunnel \
  --accept-server-license-terms \
  --name cannontunnel
```

- VS Code 'Remote Tunnel' & 'Jupyter' extensions on your laptop.

- Command‑line tools:
    - `tmux`	Keeps Jupyter alive after disconnect	￼ ￼
    - `ss` or `netstat`	Confirms Jupyter is listening	￼
    - `curl`	Quick localhost test of the tunnel	￼


---

### Step‑by‑step guide

1. Kick off / reconnect to your VS Code tunnel

```bash
sbatch vscode_tunnel.job      # your existing tunnel script
```
```bash
tail -f slurm-XXXX.out      # copy the vscode.dev/tunnel URL
```

Open that link in your browser to drop into VS Code on the compute node  ￼.

---

<!-- 2. Launch Jupyter inside a detached tmux

**⮕ VS Code terminal (inside tunnel)**
```bash
tmux new -s jupyter                            # create session
```
then, inside the new session:
```bash
conda activate env

jupyter lab --no-browser --ip=127.0.0.1 --port=8888 \
  --NotebookApp.token="MYTOKEN"  # start Jupyter
```

Verify it’s listening:
```bash
ss -ltnp | grep 8888           # LISTEN 127.0.0.1:8888 …
``` -->

---

3. Forward port 8888 in VS Code
    - Go to  **Remote Explorer → Ports** → **+** → type `8888` → *Forward*  

In theory, this only needs to be done once ever. \
Sanity‑check from VS Code’s integrated terminal:  
```bash
curl -I 'http://localhost:8888/?token=MYTOKEN'

>> HTTP 200 or 403 means the tunnel works
```

---

4.  Attach VS Code’s Jupyter extension
	1.	⇧⌘P → Jupyter: Specify Jupyter Server → Existing.
	2.	Paste http://localhost:8888/?token=MYTOKEN  ￼.
	3.	Open a notebook; pick the kernel that shows “Remote (8888)”.

The above can also be accomplished by 'Select Kernel' -> Existing -> ...
