#!/usr/bin/python
#
#   Sample Python script to read and set container easy access settings
#
#   Revision History:
#       6/2/2020        Initial release
#
import os
import json

# Import the IronBoxDX package
import sys
sys.path.append("..")
from ironboxdx.IronBoxDXRESTClient import IronBoxDXRESTClient

# Your IronBox API credentials from your web dashboard 
apiKeyPublicID = "your_api_key_public_id"
apiKeySecret = "your_api_key_secret"

# Container details
containerPublicID = "your_container_public_id"
canWrite = False
canRead = True
enabled = True
accessPassword = "your_container_access_password"

# Note: The organization that the user will be enabled/disabled will be determined
# by the organization that your API keys are associated with

def main():
    ironboxDXRestObj = IronBoxDXRESTClient(
        apiKeyPublicID = apiKeyPublicID, 
        apiKeySecret = apiKeySecret, 
        showDebugInfo= False, 
        verbose= True)

    # Get current settings
    print("Container link-based access settings are currently:")
    currentSettings = ironboxDXRestObj.management_readContainerLinkBasedAccessSettings(publicID=containerPublicID)
    print(json.dumps(currentSettings, indent=4, sort_keys=True))

    # Apply new settings
    print("Applying new link-based access settings")
    ironboxDXRestObj.management_setContainerLinkBasedAccessSettings(
        publicID=containerPublicID, 
        enabled=enabled, 
        canRead=canRead,
        canWrite=canWrite,
        accessPassword=accessPassword)

    # Get the new link-based access settings
    print("Container link-based access settings are now:")
    newSettings = ironboxDXRestObj.management_readContainerLinkBasedAccessSettings(publicID=containerPublicID)
    print(json.dumps(newSettings, indent=4, sort_keys=True))

    pass

if __name__ == "__main__":
    main()