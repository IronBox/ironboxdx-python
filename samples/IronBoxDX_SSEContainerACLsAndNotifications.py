#!/usr/bin/python
#
#   Sample Python script to modify SSE container ACLs and notification lists
#
#   Revision History:
#       10/08/2020  Initial release
#
import json

# Import the IronBoxDX package
import sys
sys.path.append("..")
from ironboxdx.IronBoxDXRESTClient import IronBoxDXRESTClient

# Your IronBox API credentials from your web dashboard 
apiKeyPublicID = "your_api_key_public_id"
apiKeySecret = "your_api_key_secret"

# Targets
containerPublicID = "container_publicID_to_modify"
customSecurityGroupPublicID = "customSecurityGroup_publicID"
notificationEmailToAdd1 = "myemail1@goironbox.com"
notificationEmailToAdd2 = "myemail2@goironbox.com"
userEmailToAdd = "acltest@goironbox.com"


def main():
    ironboxDXRestObj = IronBoxDXRESTClient(
        apiKeyPublicID = apiKeyPublicID, 
        apiKeySecret = apiKeySecret, 
        showDebugInfo = False, 
        verbose= True)

    #--------------------------------------------------------------------------
    #   Get a list of the current container notification lists and add to each
    #   list
    #--------------------------------------------------------------------------
    currentNotificationLists = ironboxDXRestObj.getContainerNotificationSettings(containerPublicID = containerPublicID)
    print("Current container notification lists:")
    print(json.dumps(currentNotificationLists, indent=4, sort_keys=True))

    # Add the notification emails to the existing lists
    currentNotificationLists["downloadNotificationList"].append(notificationEmailToAdd1)
    currentNotificationLists["uploadNotificationList"].append(notificationEmailToAdd2)
    ironboxDXRestObj.setContainerNotificationSettings(
        containerPublicID = containerPublicID, 
        uploadNotificationList = currentNotificationLists["uploadNotificationList"], 
        downloadNotificationList = currentNotificationLists["downloadNotificationList"])

    #currentNotificationLists = ironboxDXRestObj.getContainerNotificationSettings(containerPublicID)
    #print(json.dumps(currentNotificationLists, indent=4, sort_keys=True))

    #--------------------------------------------------------------------------
    #   Add a user to the container ACLs, if the email is not a registered
    #   user within the organization, it will be added to the external access
    #   lists for the container, otherwise registered access will be used.
    #
    #   If the user already exists in the ACLs, this will fail as a security
    #   precaution to preserve any existing ACLs. If you need to modify 
    #   existing ACLs for a user, remove them first and re-add with new 
    #   settings.
    #--------------------------------------------------------------------------
    addUserToACLResponse = ironboxDXRestObj.addUserToSSEContainerACLs(
        containerPublicID = containerPublicID, 
        userEmail = userEmailToAdd, 
        canRead=True,
        canWrite=True,
        # Note: This will always be False if the user is an external user, only registered users can have admin access on containers
        isAdmin=False,  
        enabled=True,
        availableUtc="", 
        expiresUtc="")
    print("Membership public ID of user {0} is {1}".format(userEmailToAdd,addUserToACLResponse["membershipRecordPublicID"]))

    #--------------------------------------------------------------------------
    #   Add a custom security group to the container ACLs
    #--------------------------------------------------------------------------
    addCustomSecurityGroupToACLResponse = ironboxDXRestObj.addCustomSecurityGroupToSSEContainerACLs(
        containerPublicID = containerPublicID,
        customSecurityGroupPublicID = customSecurityGroupPublicID,
        canRead=True,
        canWrite=True,
        isAdmin=False,
        enabled=True,
        availableUtc="", 
        expiresUtc="")
    print("Membership public ID of custom security group {0} is {1}".format(customSecurityGroupPublicID,addCustomSecurityGroupToACLResponse["membershipRecordPublicID"]))
    
    #--------------------------------------------------------------------------
    #   Read the container current ACLs
    #--------------------------------------------------------------------------
    currentContainerACLs = ironboxDXRestObj.listSSEContainerACLs(containerPublicID = containerPublicID)
    print("Current container ACLs:")
    print(json.dumps(currentContainerACLs, indent=4, sort_keys=True))

    # Clean up and remove the user and custom security group ACLs added
    ironboxDXRestObj.deleteSSEContainerACL(containerPublicID = containerPublicID, membershipPublicID = addUserToACLResponse["membershipRecordPublicID"])
    ironboxDXRestObj.deleteSSEContainerACL(containerPublicID = containerPublicID, membershipPublicID = addCustomSecurityGroupToACLResponse["membershipRecordPublicID"])


if __name__ == "__main__":
    main()