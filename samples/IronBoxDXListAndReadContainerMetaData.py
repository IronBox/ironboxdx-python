#!/usr/bin/python
#
#   Sample Python script to list the blobs in an IronBox DX server side encrypted
#   container and reads the container meta data for each using the management API
#
#   Note: 
#   You must have administrator access on the organization of the container being
#   read for meta data
#   
#   Revision History:
#       9/10/2019       Initial release
#
import os
import json

# Import the IronBoxDX package
import sys
sys.path.append("..")
from ironboxdx.IronBoxDXRESTClient import IronBoxDXRESTClient

# Your IronBox API credentials from your web dashboard (you must be an admin on the parent organization of each container read in order to retrieve its meta data)
apiKeyPublicID = "your_api_key_public_id"
apiKeySecret = "your_api_key_secret"

def main():
    ironboxDXRestObj = IronBoxDXRESTClient(
        apiKeyPublicID = apiKeyPublicID, 
        apiKeySecret = apiKeySecret, 
        showDebugInfo= False, 
        verbose= True)

    # Get a listing of containers and read the container meta data for each
    containerListingJson = ironboxDXRestObj.listSSEContainers(includeContainersQueuedForDelete=False)
    for container in containerListingJson["containers"]:
        print("Meta data for container with public ID = %s, with name = %s" % (container["containerPublicID"],container["containerName"]))
        containerMetaData = ironboxDXRestObj.management_readContainerMetaData(containerPublicID = container["containerPublicID"])
        print(json.dumps(containerMetaData, indent=4, sort_keys=True))
    pass

if __name__ == "__main__":
    main()