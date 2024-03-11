#This is to recursively transfer data from our HMS server to the Harvard FAS RC Holyoke server
# This script is to be run on HMS O2 and requires that pipx and globus-cli is installed and configured

#You will need to login to globus first AND find the endpoint IDs for both HMS and Harvard by running the following commands:
# globus endpoint search 'HMS-RC-Endpoint' and globus endpoint search 'Harvard FAS RC Holyoke'


#List endpoints 
ep1=b0718922-7031-11e9-b7f8-0a37f382de32    #HMS - use the second UUID 'HMS-RC' NOT 'HMS-RC-Endpoint'
ep2=1156ed9e-6984-11ea-af52-0201714f6eab    #Harvard

#You will have access to your directories on O2 and the Kempner cluster

from_dir=/n/data1/hms/neurobio/sabatini/Janet/file_in_dirs
to_dir=/n/holylabs/LABS/bsabatini_lab/Users/jbw25/

globus transfer $ep1:$from_dir $ep2:$to_dir --recursive --label "HMS to Harvard" 


