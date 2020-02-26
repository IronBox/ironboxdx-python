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
            blob_name=initResponse["cloubBlobStorageName"], 
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
            blob_name=initResponse["cloubBlobStorageName"], 
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
        enableUserPostResponse = self.__sendPost("dx/management/organization/user/membership/status/set/api", post_enableUser_body)
        if enableUserPostResponse.status_code != requests.codes["ok"]:
            raise Exception("Unable to set organization user status")
        enableUserResponse = enableUserPostResponse.json()
        return enableUserResponse
