#!/usr/bin/python
#
#   Sample Python script to list the blobs in an IronBox DX server side encrypted
#   container, download each ready blob and deletes the blob (optional) afterwards
#
#   Revision History:
#       9/10/2019       Initial release
#
import os
from os import path
import json

# Import the IronBoxDX package
import sys
sys.path.append("..")
from ironboxdx.IronBoxDXRESTClient import IronBoxDXRESTClient

# Your IronBox API credentials from your web dashboard
apiKeyPublicID = "your_api_key_public_id"
apiKeySecret = "your_api_key_secret"


# Download parameters
destinationFolderPath = "c:\\folder\\sub_folder"
containerPublicID = "public_id_of_container"

def main():
    ironboxDXRestObj = IronBoxDXRESTClient(
        apiKeyPublicID = apiKeyPublicID, 
        apiKeySecret = apiKeySecret,
        showDebugInfo= False, 
        verbose= True)

    #--------------------------------------------------------------------------
    # Get a listing of the blobs in the server-side encrypted container
    # State values:
    #
    #   0 = waiting for upload
    #   1 = ready 
    #--------------------------------------------------------------------------
    blobsInContainerJson = ironboxDXRestObj.listSSEContainerBlobs(containerPublicID = containerPublicID, skipPastNumItems=0, takeNumItems=500, state=1)
    print("There are %i 'ready' blobs in the container with public ID = %s:\n" % (len(blobsInContainerJson["blobs"]),blobsInContainerJson["containerPublicID"]))
    for blob in blobsInContainerJson["blobs"]:
       print(json.dumps(blob, indent=4, sort_keys=True)) 

    #--------------------------------------------------------------------------
    # Download each blob into the destionation folder path
    #--------------------------------------------------------------------------
    for blob in blobsInContainerJson["blobs"]:
        destinationFilePath = os.path.join(destinationFolderPath,blob["blobName"])
        count = 1
        while path.exists(destinationFilePath):
            # Create a new file path and recheck if it exists until we find one that doesn't
            destinationFilePath = os.path.join(destinationFolderPath,"(%i)%s" % (count,blob["blobName"]))
            count += 1

        print("Downloading blob with publicID = %s and blobName = %s to %s" % (blob["blobPublicID"], blob["blobName"], destinationFilePath))
        ironboxDXRestObj.downloadSSEContainerBlobToPath(blobPublicID = blob["blobPublicID"], destinationFilePath = destinationFilePath)

        # Delete the blob from IronBox DX (optional)
        #ironboxDXRestObj.deleteSSEContainerBlob(blobPublicID = blob["blobPublicID"])
    pass

if __name__ == "__main__":
    main()