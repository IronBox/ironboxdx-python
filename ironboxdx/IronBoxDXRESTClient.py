#   IronBox DX REST Client
#
#   Dependencies
#   ------------
#       pip install -r requirements.txt
#
#   Revision History:
#   -----------------    
#       8/6/2019    - v1.0: Implemented uploading server side encrypted (SSE) container blobs
#       8/14/2019   - v1.1: Added from text method for uploading server side encrypted (SSE) container blobs, code clean up
#       9/10/2019   - v1.2: Added download server-side encrypted (SSE) blob to file path, list SSE blobs, delete SSE blob, management read container meta data
#       9/11/2019   - v1.3: Create and delete SSE container, list storage endpoints that the user has access to
#       2/26/2020   - v1.4: Enable/disable user via management API
#       3/23/2020   - v1.5: Updated routes for enabling/disabling organization member entities (legacy was 'user', new is 'entities', both will work), 
#                           Added support for: 
#                               - List org member entities
#                               - Read org member meta data
#                               - Set container data ttl
#                               - Set container metadata
#                               - Custom security group (create, delete, update, add/remove member, list, read)
#                               - Creating organization entity
#       4/6/2020    - v1.6: Minor fix spelling mistake from REST response for initializing SSE blob (cloubBlobStorageName -> cloudBlobStorageName), 
#                           spelling mistake is kept in REST API for legacy applications, works only with version 3.0.5.26 version of REST API
#       6/1/2020    - v1.7: Added management API support for reading/setting container link-based access settings
#       8/12/2020   - v1.8: Added management API support for adding to/removing from/reading built-in security groups
#       10/7/2020   - v1.9: Add support to read/set container notification settings, list/add/remove users and custom security groups to container ACLs
#
#   Additional Information:
#   -----------------------
#       https://github.com/Azure/azure-storage-python
#
import requests
import json
import os
import sys
import io

from urllib.parse import (
    urlparse
)

from azure.storage.blob import (
    BlockBlobService,
    ContainerPermissions,
    BlobPermissions,
    PublicAccess,
)
from azure.storage.common import (
    AccessPolicy,
    ResourceTypes,
    AccountPermissions,
)


class IronBoxDXRESTClient():

    def __init__(self, apiKeyPublicID, apiKeySecret, baseAPIUrl = "https://dx-api.ironbox.app/api/v2/", verifySSLCert = True, showDebugInfo = False, verbose = True):
        self.__apiKeyPublicID = apiKeyPublicID          # Developer key public ID
        self.__apiKeySecret = apiKeySecret              # Developer key secret
        self.__baseAPIUrl = baseAPIUrl                  # The base IronBox API url
        self.__verifySSLCert = verifySSLCert            # Indicates if SSL certificates should be validated, used primarily for dev environment
        self.__showDebugInfo = showDebugInfo            # Shows debug information like REST body dummps
        self.__verbose = verbose                        # Shows human friendly information
        self.__lastUploadTotalBytes = 0                 # Size of the last upload in bytes
        return

    #--------------------------------------------------------------------------
    #   REST helpers
    #--------------------------------------------------------------------------
    # Sends HTTP POST requests
    def __sendPost(self, route, data):
        headers = { "ironbox_apikey_publicid": self.__apiKeyPublicID, "ironbox_apikey_secret" : self.__apiKeySecret }
        response = requests.post(self.__baseAPIUrl + route, json=data, headers=headers, verify=self.__verifySSLCert)
        if self.__showDebugInfo:
            print(response.status_code)
            print(response.content)
        return response

    # Outputs an object to the console
    def __debugObject(self, obj):
        if self.__showDebugInfo is True:
            print(json.dumps(obj, indent=4, sort_keys=True))
        return

    # Logs some information
    def __log(self, message):
        if self.__verbose:
            print(message)

    # Extracts the Azure storage account name from a given access signature URI
    def __extractStorageAccountName(self, accessSignatureUri):
        storage_account_name = urlparse(accessSignatureUri).hostname.split('.')[0]
        return storage_account_name

    def __progressbar(self, current, total, label="", progressBarSize=40, outstream=sys.stdout):
        def show(j):
            x = 0 if current == 0 else int(progressBarSize * (j/total))
            outstream.write("%s [%s%s] %i/%i\r" % (label, "#"*x, "."*(progressBarSize-x), j, total))
            outstream.flush()        
        show(current)
        outstream.write("\r")       # Back to the beginning of the line
        outstream.flush()
        if current == total:
            outstream.write("\n")   # On the final block go to a new line
            outstream.flush()

    #--------------------------------------------------------------------------
    #   Azure storage helpers
    #--------------------------------------------------------------------------
    def __upload_callback(self, current, total):
        if self.__verbose and (current != 0):
            #print('Uploaded ({} of {} bytes)'.format(current, total))
            self.__progressbar(current = current, total = total, label = "Uploading")
            self.__lastUploadTotalBytes = total # track total size of uploaded data
            
    def __download_callback(self, current, total):
        if self.__verbose and (current != 0):
            #print("Downloaded ({} of {} bytes)".format(current, total))
            self.__progressbar(current = current, total = total, label = "Downloading")

    #--------------------------------------------------------------------------
    #   Initializes an SSE container blob to IronBox DX
    #--------------------------------------------------------------------------
    def __initializeBlobToSSEContainer(self, containerPublicID, blobName, blobDescription = "", containerAccessPassword = ""):
        self.__log("Initializing server-side encrypted blob")
        post_initialize_body = {
            "containerPublicID" : containerPublicID,
            "blobName" : blobName,
            "blobDescription" : blobDescription,
            "containerAccessPassword" : containerAccessPassword
        }
        initPostResponse = self.__sendPost("dx/cloud/sse/blob/initialize/api", post_initialize_body)
        if initPostResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to initialize SSE blob")
        initResponse = initPostResponse.json()
        if not initResponse:
            raise Exception("Initialize SSE blob returned an invalid response")
        return initResponse
        
    #--------------------------------------------------------------------------
    #   Finalize an SSE container blob on IronBox DX
    #--------------------------------------------------------------------------
    def __finalizeBlobInSSEContainer(self, finalizeToken, blobPublicID, blobSizeBytes):
        self.__log("Finalizing server-side encrypted blob")
        post_finalize_body = {
            "finalizeToken" : finalizeToken,
            "blobPublicID" : blobPublicID,
            "originalSizeBytes" : blobSizeBytes
        }
        finalizePostResponse = self.__sendPost("dx/cloud/sse/blob/finalize/api", post_finalize_body)
        if finalizePostResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to finalize SSE blob")
        
        finalizeResponse = finalizePostResponse.json()
        # Current implementation returns empty response on finalize, so finalizeResponse will be None
        return finalizeResponse

    #--------------------------------------------------------------------------
    #   Retrieves the storage endpoints that the user has access to
    #--------------------------------------------------------------------------
    def listStorageEndpointsForUser(self):
        self.__log("Retrieving the list of storage endpoints that the current user has access to")
        post_list_body = {
        }
        listPostResponse = self.__sendPost("dx/storage/list/api", post_list_body)
        if listPostResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to get list of accessible storage endpoints")
        
        listResponse = listPostResponse.json()
        return listResponse

    #--------------------------------------------------------------------------
    #   Create a SSE container
    #--------------------------------------------------------------------------
    def createSSEContainer(self, name, storageEndpointPublicID, description="", anonymousAccessEnabled=False, anonymousAccessPassword="", humanReadableID=""):
        self.__log("Creating server-side encrypted container")
        post_create_body = {
            "name" : name,
            "description" : description,
            "anonymousAccessEnabled" : anonymousAccessEnabled,
            "anonymousAccessPassword" : anonymousAccessPassword,
            "cloudStorageEndpointPublicID" : storageEndpointPublicID,
            "humanReadableID" : humanReadableID
        }
        createPostResponse = self.__sendPost("dx/cloud/sse/container/create/api", post_create_body)
        if createPostResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to create SSE container")
        
        createResponse = createPostResponse.json()
        return createResponse

    #--------------------------------------------------------------------------
    #   Delete a SSE container
    #--------------------------------------------------------------------------
    def deleteSSEContainer(self, containerPublicID):
        self.__log("Deleting server-side encrypted container")
        post_delete_body = {
            "containerPublicID" : containerPublicID
        }
        deletePostResponse = self.__sendPost("dx/cloud/sse/container/delete/api", post_delete_body)
        if deletePostResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to delete SSE container")
        
        deleteResponse = deletePostResponse.json()
        return deleteResponse

    #--------------------------------------------------------------------------
    #   Get list of SSE containers
    #--------------------------------------------------------------------------
    def listSSEContainers(self, includeContainersQueuedForDelete = False):
        post_list_body = {
            "includeContainersQueuedForDelete" : includeContainersQueuedForDelete
        }
        listPostResponse = self.__sendPost("dx/cloud/sse/containers/get/api", post_list_body)
        if (listPostResponse.status_code != requests.codes["ok"]):
            raise Exception("Unable to list server-side encrypted containers")
        listResponse = listPostResponse.json()
        return listResponse

    #--------------------------------------------------------------------------
    #   Get list of blobs in an SSE container
    #   
    #   State table:
    #       0 = Waiting for upload
    #       1 = Ready
    #--------------------------------------------------------------------------
    def listSSEContainerBlobs(self, containerPublicID, skipPastNumItems = 0, takeNumItems = 500, state = 1):
        self.__log("Listing server-side encrypted blobs")
        post_list_body = {
            "containerPublicID" : containerPublicID,
            "skipPastNumItems" : skipPastNumItems,
            "takeNumItems" : takeNumItems,
            "state" : state
        }
        listPostResponse = self.__sendPost("dx/cloud/sse/blob/get/api", post_list_body)
        if (listPostResponse.status_code != requests.codes["ok"]):
            raise Exception("Unable to list server-side encrypted blobs")
        listResponse = listPostResponse.json()
        return listResponse

    #--------------------------------------------------------------------------
    #   Deletes a SSE container blob
    #--------------------------------------------------------------------------
    def deleteSSEContainerBlob(self, blobPublicID):
        self.__log("Deleting server-side encrypted blob")
        post_delete_body = {
            "blobPublicID" : blobPublicID
        }
        deletePostResponse = self.__sendPost("dx/cloud/sse/blob/delete/api", post_delete_body)
        if (deletePostResponse.status_code != requests.codes["ok"]):
            raise Exception("Unable to delete server-side encrypted blob")
        deleteResponse = deletePostResponse.json()
        self.__log("Delete complete")
        # delete response is empty, will be used in the future possibly
        #return deleteResponse


    #--------------------------------------------------------------------------
    #   Downloads a specified SSE blob to a given destination path
    #--------------------------------------------------------------------------
    def downloadSSEContainerBlobToPath(self, blobPublicID, destinationFilePath):

        self.__log("Downloading server-side encrypted blob with publicID = %s" % (blobPublicID))
        post_download_body = {
            "blobPublicID" : blobPublicID
        }
        downloadPostResponse = self.__sendPost("dx/cloud/sse/blob/download/api", post_download_body)
        if downloadPostResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to download SSE blob")
        downloadResponse = downloadPostResponse.json()
        storage_account_name = self.__extractStorageAccountName(downloadResponse["accessSignatureUri"])   # Extract the Azure account name
        self.sas_service = BlockBlobService(account_name=storage_account_name, sas_token=downloadResponse["accessToken"])
        self.sas_service.get_blob_to_path(
            file_path=destinationFilePath,
            blob_name=downloadResponse["cloudBlobStorageName"], 
            container_name=downloadResponse["cloudContainerStorageName"],
            progress_callback=self.__download_callback)
        
        self.__log("Download complete")

    #--------------------------------------------------------------------------
    #   Uploads a specified file path as a blob to a server-side encrypted 
    #   IronBox DX container
    #--------------------------------------------------------------------------
    def uploadBlobToSSEContainerFromPath(self, containerPublicID, blobName, sourceFilePath, blobDescription = "", containerAccessPassword = ""):

        
        self.__log("Uploading [{}] to server-side encrypted container with public ID [{}] as blob with name [{}]".format(sourceFilePath, containerPublicID, blobName))

        # Initialize an SSE blob
        initResponse = self.__initializeBlobToSSEContainer(containerPublicID=containerPublicID, blobName=blobName, blobDescription=blobDescription, containerAccessPassword=containerAccessPassword)

        # Upload the contents to storage backend, create a account service reference from the 
        # shared access signature we received from the initialization process
        self.__log("Uploading contents to cloud storage")
        storage_account_name = self.__extractStorageAccountName(initResponse["accessSignatureUri"])   # Extract the Azure account name
        self.sas_service = BlockBlobService(account_name=storage_account_name, sas_token=initResponse["accessToken"])
        self.sas_service.create_blob_from_path(
            file_path=sourceFilePath, 
            progress_callback=self.__upload_callback, 
            blob_name=initResponse["cloudBlobStorageName"], 
            container_name=initResponse["cloudContainerStorageName"])
        
        # Signal that the upload is completed
        #st = os.stat(sourceFilePath)
        finalizeResponse = self.__finalizeBlobInSSEContainer(
            finalizeToken=initResponse['finalizeToken'], 
            blobPublicID=initResponse['blobPublicID'], 
            #blobSizeBytes=st.st_size
            blobSizeBytes=self.__lastUploadTotalBytes
        )
        
        # Done
        self.__log("Upload complete")
        

    #--------------------------------------------------------------------------
    #   Uploads a specified text string as a blob to a server-side encrypted 
    #   IronBox DX container
    #--------------------------------------------------------------------------
    def uploadBlobToSSEContainerFromText(self, containerPublicID, blobName, sourceText, encoding = "utf-8",  blobDescription = "", containerAccessPassword = ""):

        self.__log("Uploading text to server-side encrypted container with public ID [{}] as blob with name [{}]".format(containerPublicID, blobName))

        # Initialize an SSE blob
        initResponse = self.__initializeBlobToSSEContainer(containerPublicID=containerPublicID, blobName=blobName,  blobDescription=blobDescription, containerAccessPassword=containerAccessPassword)

        # Upload the contents to storage backend, create a account service reference from the 
        # shared access signature we received from the initialization process
        self.__log("Uploading contents to cloud storage")
        storage_account_name = self.__extractStorageAccountName(initResponse["accessSignatureUri"])   # Extract the Azure account name
        self.sas_service = BlockBlobService(account_name=storage_account_name, sas_token=initResponse["accessToken"])
        self.sas_service.create_blob_from_text(
            text=sourceText, 
            encoding=encoding, 
            progress_callback=self.__upload_callback, 
            blob_name=initResponse["cloudBlobStorageName"], 
            container_name=initResponse["cloudContainerStorageName"]
        )

        # Signal that the upload is completed
        finalizeResponse = self.__finalizeBlobInSSEContainer(
            finalizeToken=initResponse['finalizeToken'], 
            blobPublicID=initResponse['blobPublicID'], 
            blobSizeBytes=self.__lastUploadTotalBytes
        )
        
        # Done
        self.__log("Upload complete")


    #--------------------------------------------------------------------------
    #   Reads the notification settings for a container (SSE or CSE)
    #--------------------------------------------------------------------------
    def getContainerNotificationSettings(self, containerPublicID):
        self.__log("Reading container notification settings")
        post_notification_body = {
            "containerPublicID" : containerPublicID
        }
        notificationPostResponse = self.__sendPost("dx/cloud/container/notification/get/api", post_notification_body)
        if (notificationPostResponse.status_code != requests.codes["ok"]):
            raise Exception("Unable to read container notification settings")
        notificationResponse = notificationPostResponse.json()
        self.__log("Read container notification settings completed")
        return notificationResponse


    #--------------------------------------------------------------------------
    #   Sets the notification settings for a container (SSE or CSE)
    #--------------------------------------------------------------------------
    def setContainerNotificationSettings(self, containerPublicID, uploadNotificationList, downloadNotificationList):
        self.__log("Setting container notification settings")
        post_notification_body = {
            "containerPublicID" : containerPublicID,
            "uploadNotificationList" : uploadNotificationList,
            "downloadNotificationList" : downloadNotificationList
        }
        notificationPostResponse = self.__sendPost("dx/cloud/container/notification/set/api", post_notification_body)
        if (notificationPostResponse.status_code != requests.codes["ok"]):
            raise Exception("Unable to set container notification settings")
        notificationResponse = notificationPostResponse.json()
        self.__log("Set container notification settings completed")
        return notificationResponse

    #--------------------------------------------------------------------------
    #   Adds a user to a SSE container's ACLs
    #--------------------------------------------------------------------------
    def addUserToSSEContainerACLs(self, containerPublicID, userEmail, canRead, canWrite, isAdmin, enabled, availableUtc = "", expiresUtc = ""):
        self.__log("Adding user to server-side encrypted container ACLs")
        post_sseContainerACL_body = {
            "containerPublicID" : containerPublicID,
            "userEmail" : userEmail,
            "canRead" : canRead,
            "canWrite" : canWrite,
            "isAdmin" : isAdmin,
            "enabled" : enabled,
            "availableUtc" : availableUtc,
            "expiresUtc" : expiresUtc
        }
        sseACLPostResponse = self.__sendPost("dx/cloud/sse/containers/acl/add/api", post_sseContainerACL_body)
        if (sseACLPostResponse.status_code != requests.codes["ok"]):
            raise Exception("Unable to add user to server-side encrypted container ACLs")
        sseACLResponse = sseACLPostResponse.json()
        self.__log("Add user to SSE container ACLs completed")
        return sseACLResponse

    #--------------------------------------------------------------------------
    #   Adds a custom security group to a SSE container's ACLs
    #--------------------------------------------------------------------------
    def addCustomSecurityGroupToSSEContainerACLs(self, containerPublicID, customSecurityGroupPublicID, canRead, canWrite, isAdmin, enabled, availableUtc = "", expiresUtc = ""):
        self.__log("Adding custom security group to server-side encrypted container ACLs")
        post_sseContainerACL_body = {
            "containerPublicID" : containerPublicID,
            "customSecurityGroupPublicID" : customSecurityGroupPublicID,
            "canRead" : canRead,
            "canWrite" : canWrite,
            "isAdmin" : isAdmin,
            "enabled" : enabled,
            "availableUtc" : availableUtc,
            "expiresUtc" : expiresUtc
        }
        sseACLPostResponse = self.__sendPost("dx/cloud/sse/containers/acl/secgroups/custom/add/api", post_sseContainerACL_body)
        if (sseACLPostResponse.status_code != requests.codes["ok"]):
            raise Exception("Unable to add custom security group to server-side encrypted container ACLs")
        sseACLResponse = sseACLPostResponse.json()
        self.__log("Add custom security group to SSE container ACLs completed")
        return sseACLResponse

    #--------------------------------------------------------------------------
    #   Removes a single SSE container ACL
    #--------------------------------------------------------------------------
    def deleteSSEContainerACL(self, containerPublicID, membershipPublicID):
        self.__log("Removing server-side encrypted container ACL")
        post_sseContainerACL_body = {
            "containerPublicID" : containerPublicID,
            "membershipPublicID" : membershipPublicID
        }
        sseACLPostResponse = self.__sendPost("dx/cloud/sse/containers/acl/delete/api", post_sseContainerACL_body)
        if (sseACLPostResponse.status_code != requests.codes["ok"]):
            raise Exception("Unable to remove server-side encrypted container ACL")
        sseACLResponse = sseACLPostResponse.json()
        self.__log("Remove SSE container ACL completed")
        return sseACLResponse

    #--------------------------------------------------------------------------
    #   Reads the ACLs for a SSE container
    #--------------------------------------------------------------------------
    def listSSEContainerACLs(self, containerPublicID):
        self.__log("Reading server-side encrypted container ACLs")
        post_sseContainerACL_body = {
            "publicID" : containerPublicID
        }
        sseACLPostResponse = self.__sendPost("dx/cloud/sse/containers/acl/list/api", post_sseContainerACL_body)
        if (sseACLPostResponse.status_code != requests.codes["ok"]):
            raise Exception("Unable to read server-side encrypted container ACLs")
        sseACLResponse = sseACLPostResponse.json()
        self.__log("SSE container ACLs listing completed")
        return sseACLResponse


    '''
    Note: Management API calls must use API keys whose owners are administrators of their
    organizations for these calls to work
    '''

    #--------------------------------------------------------------------------
    #   Reads the meta data for a container
    #--------------------------------------------------------------------------
    def management_readContainerMetaData(self, containerPublicID):
        self.__log("Reading container meta data for container with public ID [{}]".format(containerPublicID))
        post_readmetadata_body = {
            "containerPublicID" : containerPublicID
        }
        readMetaDataPostResponse = self.__sendPost("dx/management/container/metadata/api", post_readmetadata_body)
        if readMetaDataPostResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to read meta data for blob")
        readMetaDataResponse = readMetaDataPostResponse.json()
        return readMetaDataResponse


    #--------------------------------------------------------------------------
    #   Enable/disable entity organization membership status
    #--------------------------------------------------------------------------
    def management_setEntityOrganizationMembershipStatus(self, memberEmail, enabled):
        self.__log("Setting organization membership for user [{}] to {}".format(memberEmail, enabled))
        post_enableUser_body = {
            "memberEmail" : memberEmail,
            "enabled" : enabled
        }
        enableUserPostResponse = self.__sendPost("dx/management/organization/entities/membership/status/set/api", post_enableUser_body)
        if enableUserPostResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to set organization user status")
        enableUserResponse = enableUserPostResponse.json()
        return enableUserResponse

    #--------------------------------------------------------------------------
    #   Create an entity organization membership status
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
    #--------------------------------------------------------------------------
    def management_createOrganizationEntity(self, memberEmail, memberPassword, enabled):
        self.__log("Creating an organization entity account for {}, enabled = {}".format(memberEmail, enabled))
        post_createUser_body = {
            "email" : memberEmail,
            "password" : memberPassword,
            "enabled" : enabled
        }
        createUserPostResponse = self.__sendPost("dx/management/organization/entities/create/api", post_createUser_body)
        if createUserPostResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to create organization entity")
        createUserResponse = createUserPostResponse.json()
        return createUserResponse

    #--------------------------------------------------------------------------
    #   List the member entities of an organization
    #--------------------------------------------------------------------------
    def management_listOrganizationMemberEntities(self, skipPastNumItems = 0, takeNumItems = -1):
        self.__log("Listing organization members")
        post_listOrgMemberEntities_body = {
            "skipPastNumItems" : skipPastNumItems,
            "takeNumItems" : takeNumItems
        }
        listOrgMembersPostResponse = self.__sendPost("dx/management/organization/entities/api", post_listOrgMemberEntities_body)
        if listOrgMembersPostResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to list organization member entities")
        listOrgMembersResponse = listOrgMembersPostResponse.json()
        return listOrgMembersResponse
    
    #--------------------------------------------------------------------------
    #   Get an organization member entity meta data
    #--------------------------------------------------------------------------
    def management_readOrganizationMemberEntityMetadata(self, memberPublicID):
        self.__log("Reading organization member entity meta data for user with publicID = {}".format(memberPublicID))
        post_readOrgMemberEntityMetadata_body = {
            "memberPublicID" : memberPublicID
        }
        readOrgMemberEntityMetadataPostResponse = self.__sendPost("dx/management/organization/entities/metadata/api", post_readOrgMemberEntityMetadata_body)
        if readOrgMemberEntityMetadataPostResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to read organization member entity metadata")
        readOrgMemberEntityMetadataResponse = readOrgMemberEntityMetadataPostResponse.json()
        return readOrgMemberEntityMetadataResponse

    #--------------------------------------------------------------------------
    #   Sets the data ttl value for a container
    #   Note: This requires that the organization has custom container data 
    #   ttl enabled, contact the IronBox team to enable this
    #--------------------------------------------------------------------------
    def management_setContainerDataTtl(self, containerPublicID, containerDataTTLHours, containerDataTTLEnabled):
        self.__log("Setting data ttl for container with publicID = {}".format(containerPublicID))
        post_body = {
            "containerPublicID" : containerPublicID,
            "containerDataTTLHours" : containerDataTTLHours,
            "containerDataTTLEnabled" : containerDataTTLEnabled
        }
        postResponse = self.__sendPost("dx/management/container/datattl/api", post_body)
        if postResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to set container data ttl")
        response = postResponse.json()
        return response

    #--------------------------------------------------------------------------
    #   Sets meta data for a container
    #   Valid values for metaDataTarget:
    #   
    #   0 = Migrated IronBoxSFT ContainerID
    #--------------------------------------------------------------------------
    def management_setContainerMetadata(self, containerPublicID, metaDataTarget, metaDataValue):
        self.__log("Setting metadata for container with publicID = {}".format(containerPublicID))
        post_body = {
            "containerPublicID" : containerPublicID,
            "metaDataTarget" : metaDataTarget,
            "metaDataValue" : metaDataValue
        }
        postResponse = self.__sendPost("dx/management/container/metadata/set/api", post_body)
        if postResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to set container metadata")
        response = postResponse.json()
        return response

    #--------------------------------------------------------------------------
    #   Creates a custom security group
    #--------------------------------------------------------------------------
    def management_createCustomSecurityGroup(self, name, enabled):
        self.__log("Creating custom security group named = {}, enabled = {}".format(name,enabled))
        post_body = {
            "name" : name,
            "enabled" : enabled
        }
        postResponse = self.__sendPost("dx/management/organization/secgroups/custom/create/api", post_body)
        if postResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to create custom security group")
        response = postResponse.json()
        return response

    #--------------------------------------------------------------------------
    #   Deletes a custom security group
    #--------------------------------------------------------------------------
    def management_deleteCustomSecurityGroup(self, publicID):
        self.__log("Deleting custom security group with publicID {}".format(publicID))
        post_body = {
            "publicID" : publicID
        }
        postResponse = self.__sendPost("dx/management/organization/secgroups/custom/delete/api", post_body)
        if postResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to delete custom security group")
        response = postResponse.json()
        return response

    #--------------------------------------------------------------------------
    #   Updates a custom security group
    #--------------------------------------------------------------------------
    def management_updateCustomSecurityGroup(self, publicID, name, enabled):
        self.__log("Updating custom security group with publicID {}".format(publicID))
        post_body = {
            "publicID" : publicID,
            "name" : name,
            "enabled" : enabled
        }
        postResponse = self.__sendPost("dx/management/organization/secgroups/custom/update/api", post_body)
        if postResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to update custom security group")
        response = postResponse.json()
        return response

    #--------------------------------------------------------------------------
    #   Adds a member to a custom security group
    #--------------------------------------------------------------------------
    def management_addMemberToCustomSecurityGroup(self, publicID, memberEmail):
        self.__log("Adding member to custom security group with publicID {}, email = {}".format(publicID, memberEmail))
        post_body = {
            "publicID" : publicID,
            "memberEmail" : memberEmail
        }
        postResponse = self.__sendPost("dx/management/organization/secgroups/custom/addmember/api", post_body)
        if postResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to add member to custom security group")
        response = postResponse.json()
        return response

    #--------------------------------------------------------------------------
    #   Removes a member from a custom security group
    #--------------------------------------------------------------------------
    def management_removeMemberFromCustomSecurityGroup(self, publicID, memberEmail):
        self.__log("Removing member from custom security group with publicID {}, email = {}".format(publicID, memberEmail))
        post_body = {
            "publicID" : publicID,
            "memberEmail" : memberEmail
        }
        postResponse = self.__sendPost("dx/management/organization/secgroups/custom/removemember/api", post_body)
        if postResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to remove member from custom security group")
        response = postResponse.json()
        return response

    #--------------------------------------------------------------------------
    #   List custom security groups
    #--------------------------------------------------------------------------
    def management_listCustomSecurityGroups(self):
        self.__log("Listing custom security groups")
        post_body = {
            # No body required for this call
        }
        postResponse = self.__sendPost("dx/management/organization/secgroups/custom/api", post_body)
        if postResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to list custom security groups")
        response = postResponse.json()
        return response

    #--------------------------------------------------------------------------
    #   Read custom security group
    #--------------------------------------------------------------------------
    def management_readCustomSecurityGroup(self, publicID):
        self.__log("Reading custom security group with publicID = {}".format(publicID))
        post_body = {
            "publicID" : publicID
        }
        postResponse = self.__sendPost("dx/management/organization/secgroups/custom/read/api", post_body)
        if postResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to read custom security group")
        response = postResponse.json()
        return response

    #--------------------------------------------------------------------------
    #   Read container link-based access settings
    #--------------------------------------------------------------------------
    def management_readContainerLinkBasedAccessSettings(self, publicID):
        self.__log("Reading container link-based access settings with publicID = {}".format(publicID))
        post_body = {
            "publicID" : publicID
        }
        postResponse = self.__sendPost("dx/management/container/settings/linkbased/api", post_body)
        if postResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to read container link-based settings")
        response = postResponse.json()
        return response

    #--------------------------------------------------------------------------
    #   Set container link-based access settings
    #--------------------------------------------------------------------------
    def management_setContainerLinkBasedAccessSettings(self, publicID, enabled, canRead, canWrite, accessPassword):
        self.__log("Setting container link-based access settings with publicID = {}".format(publicID))
        post_body = {
            "publicID" : publicID,
            "enabled" : enabled,
            "canRead" : canRead,
            "canWrite" : canWrite,
            "accessPassword" : accessPassword
        }
        postResponse = self.__sendPost("dx/management/container/settings/linkbased/set/api", post_body)
        if postResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to set container link-based settings")
        response = postResponse.json()
        return response

    #--------------------------------------------------------------------------
    #   Add to built-in security group
    #--------------------------------------------------------------------------
    def management_addMemberToBuiltInSecurityGroup(self, groupName, memberEmail):
        self.__log("Adding member {} to built-in security group {}".format(memberEmail,groupName))
        post_body = {
            "groupName" : groupName,
            "memberEmail" : memberEmail,
        }
        postResponse = self.__sendPost("dx/management/organization/secgroups/builtin/addmember/api", post_body)
        if postResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to add member to built-in security group")
        response = postResponse.json()
        return response

    #--------------------------------------------------------------------------
    #   Remove from built-in security group
    #--------------------------------------------------------------------------
    def management_removeMemberFromBuiltInSecurityGroup(self, groupName, memberEmail):
        self.__log("Removing member {} from built-in security group {}".format(memberEmail,groupName))
        post_body = {
            "groupName" : groupName,
            "memberEmail" : memberEmail,
        }
        postResponse = self.__sendPost("dx/management/organization/secgroups/builtin/removemember/api", post_body)
        if postResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to remove member from built-in security group")
        response = postResponse.json()
        return response

    #--------------------------------------------------------------------------
    #   Read bulit-in security group
    #--------------------------------------------------------------------------
    def management_readBuiltInSecurityGroup(self, groupName):
        self.__log("Reading built-in security group {}".format(groupName))
        post_body = {
            "groupName" : groupName
        }
        postResponse = self.__sendPost("dx/management/organization/secgroups/builtin/read/api", post_body)
        if postResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to read built-in security group")
        response = postResponse.json()
        return response