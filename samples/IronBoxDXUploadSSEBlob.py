#!/usr/bin/python
#
#   Sample Python script to upload a file to an IronBox DX server-side encrypted container
#
#   Revision History:
#       8/6/2019        Initial release
#       8/14/2019       Added text based uploading sample
#
import os

# Import the IronBoxDX package
import sys
sys.path.append("..")
from ironboxdx.IronBoxDXRESTClient import IronBoxDXRESTClient

# Your IronBox API credentials from your web dashboard 
apiKeyPublicID = "your_api_key_public_id"
apiKeySecret = "your_api_key_secret"
containerPublicID = "public_id_of_container_to_upload_to"

# Upload parameters based on file path upload
sourceFilePath = "x:\\folder\\fileToUpload.ext"
filePathUploadBlobName = os.path.basename(sourceFilePath)

# Upload parameters based on text upload
textUploadBody = "Sample content from text upload"
textUploadBlobName = "TextUploadBlob.txt"

def main():
    ironboxDXRestObj = IronBoxDXRESTClient(
        apiKeyPublicID = apiKeyPublicID, 
        apiKeySecret = apiKeySecret, 
        showDebugInfo= False, 
        verbose= True)

    # Upload a server-side encrypted blob using a source path
    ironboxDXRestObj.uploadBlobToSSEContainerFromPath(containerPublicID=containerPublicID, blobName=filePathUploadBlobName, sourceFilePath=sourceFilePath)

    # Upload a server-side encrypted blob using text string as the source
    ironboxDXRestObj.uploadBlobToSSEContainerFromText(containerPublicID=containerPublicID, blobName=textUploadBlobName, sourceText=textUploadBody)
    pass

if __name__ == "__main__":
    main()