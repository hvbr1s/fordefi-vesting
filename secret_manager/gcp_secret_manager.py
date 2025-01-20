from google.cloud import secretmanager


# Helper function to fetch a secret from GCP's Secret Manager
def access_secret(project_id, secret_id, version_id):

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})

    return response.payload.data.decode('UTF-8')