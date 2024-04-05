#!/bin/bash

# This script will create a secret environment variable

## Check if a name for the secret environment variable is provided
### If first argument is empty, print an error message and exit
if [ -z "$1" ]; then
  echo "Please provide a name for the secret environment variable"
  exit 1
fi

## Get the value for the secret environment variable
### "read": prompt the user to enter a value, "-s": silent mode, "-p": prompt message, "SECRET_VALUE": variable to store the value
read -sp "Enter Secret Value: " SECRET_VALUE
echo  ## Move to a new line

## Create the secret environment variable
declare -x $1=$SECRET_VALUE

## Print a success message
echo "Secret environment variable $1 created successfully"