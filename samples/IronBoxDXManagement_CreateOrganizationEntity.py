#!/usr/bin/python
#
#   Sample Python script to create an organization entity/user
#
#   Remarks:
#   - The entity/user must not already exist
#   - The organization that the API key belongs to must have 'security
#     authority' over the domain of the user. Example: If you are trying to 
#     create the user test@domain.com, the parent organization of the API
#     key being used must have security authority over the domain "domain.com"
#     (ask your IronBox team representative to configure this)
#   - Password must comply with parent organization security policy
#   - If you are creating the entity with its organization membership enabled,
#     that organization must have available user licenses available.
#     You can create unlimited number of disabled user accounts
#
#   Revision History:
#       3/24/2020        Initial release
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
memberEmail = "email_of_user_to_create"
memberPassword = "password_of_user_to_create"
enabled = True

# Note: The organization that the user will be enabled/disabled will be determined
# by the organization that your API keys are associated with

def main():
    ironboxDXRestObj = IronBoxDXRESTClient(
        apiKeyPublicID = apiKeyPublicID, 
        apiKeySecret = apiKeySecret, 
        showDebugInfo= False, 
        verbose= True)

    # Create the organization entity
    ironboxDXRestObj.management_createOrganizationEntity(memberEmail=memberEmail, memberPassword=memberPassword, enabled=enabled)

    pass

if __name__ == "__main__":
    main()