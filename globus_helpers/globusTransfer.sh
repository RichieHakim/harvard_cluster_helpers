#!/bin/bash

## Script for transfer between HMS/O2 <--> Harvard FAS RC Holyoke
## Uses globus-cli. Install with:
## python -m pip install pipx
## pipx install globus-cli

## You will need to login to globus first AND find the endpoint IDs for both HMS and Harvard by running the following commands:
## globus endpoint search 'HMS-RC-Endpoint' and globus endpoint search 'Harvard FAS RC Holyoke'


# Process inputs
name_from=$1
path_from=$2
name_to=$3
path_to=$4
## All other input args are appended to the globus transfer command
shift 4

# List endpoints
declare -A endpoints=(
    [hms]=b0718922-7031-11e9-b7f8-0a37f382de32
    [fas]=1156ed9e-6984-11ea-af52-0201714f6eab
)

# Map names to endpoints
ep_from=${endpoints[$name_from]}
ep_to=${endpoints[$name_to]}

# Check if endpoints were correctly assigned
if [ -z "$ep_from" ]; then
    echo "Invalid endpoint_from name: $name_from"
    exit 1
elif [ -z "$ep_to" ]; then
    echo "Invalid endpoint_to name: $name_to"
    exit 1
fi

# Perform the Globus transfer
echo ""
echo "globus transfer $ep_from:$path_from $ep_to:$path_to --label '$name_from to $name_to' $@"
# Replace echo with actual command call when ready
globus transfer $ep_from:$path_from $ep_to:$path_to --label "$name_from to $name_to" $@