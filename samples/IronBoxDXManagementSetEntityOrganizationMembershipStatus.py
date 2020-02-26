#!/usr/bin/python
#
#   Sample Python script to enable or disable an organization user
#
#   Revision History:
#       2/26/2020        Initial release
#
import os

# Import the IronBoxDX package
import sys
sys.path.append("..")
from ironboxdx.IronBoxDXRESTClient import IronBoxDXRESTClient

# Your IronBox API credentials from your web dashboard 
apiKeyPublicID = "your_api_key_public_id"
apiKeySecret = "your_api_key_secret"

# Email of user to enable and enabled status (True = enabled, False = disabled)
memberEmail = "email_of_user_to_enable_disable"
enabled = True

# Note: The organization that the user will be enabled/disabled will be determined
# by the organization that your API keys are associated with

def main():
    ironboxDXRestObj = IronBoxDXRESTClient(
        apiKeyPublicID = apiKeyPublicID, 
        apiKeySecret = apiKeySecret, 
        showDebugInfo= False, 
        verbose= True)

    # Enable or disable the user's organization membership
    ironboxDXRestObj.management_setEntityOrganizationMembershipStatus(memberEmail=memberEmail, enabled=enabled)

    pass

if __name__ == "__main__":
    main()