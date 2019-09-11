#!/usr/bin/python
#
#   Sample Python script create and delete SSE containers
#
#   Revision History:
#       9/11/2019       Initial release
#
import json

# Import the IronBoxDX package
import sys
sys.path.append("..")
from ironboxdx.IronBoxDXRESTClient import IronBoxDXRESTClient

# Your IronBox API credentials from your web dashboard 
apiKeyPublicID = "your_api_key_public_id"
apiKeySecret = "your_api_key_secret"

def main():
    ironboxDXRestObj = IronBoxDXRESTClient(
        apiKeyPublicID = apiKeyPublicID, 
        apiKeySecret = apiKeySecret, 
        showDebugInfo= False, 
        verbose= True)

    #--------------------------------------------------------------------------
    # Get a list of the storage endpoints that the user has access to
    #--------------------------------------------------------------------------
    listResponseJson = ironboxDXRestObj.listStorageEndpointsForUser()
    print("There are %i storage endpoints the current user has access to:" % len(listResponseJson["endpoints"]))
    for storageEndpoint in listResponseJson["endpoints"]:
        print(json.dumps(storageEndpoint, indent=4, sort_keys=True))

    #--------------------------------------------------------------------------
    # Create a SSE container on the selected storage endpoint
    #--------------------------------------------------------------------------
    createJsonResponse = ironboxDXRestObj.createSSEContainer(
        name="My Test Container", 
        storageEndpointPublicID=listResponseJson["endpoints"][0]["publicID"],   # Just select the first storage endpoint
        description="Description of your new container (optional)",
        anonymousAccessEnabled=False,
        anonymousAccessPassword="Only set this if you want to set a password on anonymous link-based accessed containers, will be ignored if anonymousAccessEnabled flag is False (optional)",
        humanReadableID="A field you can use to set internally used IDs (optional)")
    print("The public ID of the container created is " + createJsonResponse["containerPublicID"])

    #--------------------------------------------------------------------------
    # Delete the container
    #--------------------------------------------------------------------------
    deleteJsonResponse = ironboxDXRestObj.deleteSSEContainer(containerPublicID=createJsonResponse["containerPublicID"])
    if (deleteJsonResponse != None):
        print("Delete container successful")
    else:
        print("Unable to delete container")

    pass

if __name__ == "__main__":
    main()