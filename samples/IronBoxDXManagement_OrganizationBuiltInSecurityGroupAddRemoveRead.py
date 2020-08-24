#!/usr/bin/python
#
#   Sample Python script to add/remove/read organization entities to built-in security groups
#
#   Remarks:
#   The following group names are supported:
#       - sse_creators      (add/remove/read)
#       - sse_readers       (add/remove/read)
#       - administrators    (read)
#       - developers        (read)
#
#   Revision History:
#       8/12/2020        Initial release
#
import os
import json

# Import the IronBoxDX package
import sys
sys.path.append("..")
from ironboxdx.IronBoxDXRESTClient import IronBoxDXRESTClient

# Your IronBox API credentials from your web dashboard, you must be an 
# organization administrator
apiKeyPublicID = "your_api_key_public_id"
apiKeySecret = "your_api_key_secret"

# Email of target user to add/remove, must exist in your organization already
memberEmail = "email_of_user"
groupName = "sse_creators"

def main():
    ironboxDXRestObj = IronBoxDXRESTClient(
        apiKeyPublicID = apiKeyPublicID, 
        apiKeySecret = apiKeySecret, 
        showDebugInfo = False, 
        verbose = True)

    # List the members of the security group
    groupInfo = ironboxDXRestObj.management_readBuiltInSecurityGroup(groupName=groupName)
    print(json.dumps(groupInfo, indent=4, sort_keys=True))

    # Add a user to the security group
    print("Starting add ...")
    addResult = ironboxDXRestObj.management_addMemberToBuiltInSecurityGroup(groupName=groupName,memberEmail=memberEmail)

    # List the members of the security group, new member should be added
    print("Group membership after add")
    groupInfo = ironboxDXRestObj.management_readBuiltInSecurityGroup(groupName=groupName)
    print(json.dumps(groupInfo, indent=4, sort_keys=True))

    # Remove the user from the security group
    print("Trying remove ...")
    removeResult = ironboxDXRestObj.management_removeMemberFromBuiltInSecurityGroup(groupName=groupName,memberEmail=memberEmail)

    # List the members of the security group, new member should be removed
    print("Group membership after remove")
    groupInfo = ironboxDXRestObj.management_readBuiltInSecurityGroup(groupName=groupName)
    print(json.dumps(groupInfo, indent=4, sort_keys=True))

    pass

if __name__ == "__main__":
    main()